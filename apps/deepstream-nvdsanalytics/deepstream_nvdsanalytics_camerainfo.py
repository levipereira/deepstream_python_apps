#!/usr/bin/env python3

################################################################################
# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
################################################################################

"""
DeepStream nvdsanalytics sample application using nvmultiurisrcbin

This application demonstrates:
1. Using nvmultiurisrcbin with REST API support for dynamic source management
2. Accessing camera metadata (camera_id, source_id) after nvdsanalytics
3. Processing analytics data with camera identification
4. Dynamic source addition/removal via REST API ONLY

Usage:
    python3 deepstream_nvdsanalytics_multiuri.py
    
    # Add sources dynamically via REST API:
    curl -X POST http://localhost:9000/api/v1/streams \
      -H "Content-Type: application/json" \
      -d '{
        "camera_id": "camera_001",
        "camera_url": "rtsp://192.168.1.100:554/stream",
        "camera_name": "Main Entrance"
      }'
      
Note: This application does NOT accept command line arguments for sources.
All sources must be added via REST API after the application starts.
"""

import sys
sys.path.append('../')
import gi
import configparser
gi.require_version('Gst', '1.0')
from gi.repository import GLib, Gst
from ctypes import *
import time
import sys
import math
import platform
from common.platform_info import PlatformInfo
from common.bus_call import bus_call

import pyds

MAX_DISPLAY_LEN = 64
PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3
MUXER_OUTPUT_WIDTH = 1920
MUXER_OUTPUT_HEIGHT = 1080
MUXER_BATCH_TIMEOUT_USEC = 33000
TILED_OUTPUT_WIDTH = 1280
TILED_OUTPUT_HEIGHT = 720
GST_CAPS_FEATURES_NVMM = "memory:NVMM"
OSD_PROCESS_MODE = 0
OSD_DISPLAY_TEXT = 1
pgie_classes_str = ["Vehicle", "TwoWheeler", "Person", "RoadSign"]

# REST API configuration
REST_API_PORT = "9000"
REST_API_IP = "localhost"

# Camera metadata type definition (must match C implementation)
try:
    NVDS_GST_META_CAMERA_INFO = pyds.nvds_get_user_meta_type("NVIDIA.NVDS_GST_META_CAMERA_INFO")
except Exception as e:
    print(f"Warning: Could not register custom metadata type: {e}")
    NVDS_GST_META_CAMERA_INFO = None

# CLEAN IMPLEMENTATION: Removed global storage functions - using only NvDsUserMeta

def get_camera_metadata_from_frame(frame_meta):
    """
    CLEAN IMPLEMENTATION: Extract camera metadata using ONLY NvDsUserMeta
    Following deepstream_user_metadata_app.c pattern exactly
    """
    camera_info = {
        'camera_id': None,
        'source_id': frame_meta.source_id,
        'camera_name': None,
        'camera_url': None
    }
    
    # NVIDIA OFFICIAL PATTERN: Access frame-level user metadata
    # Based on deepstream_user_metadata_app.c osd_sink_pad_buffer_probe function
    l_user = frame_meta.frame_user_meta_list  # Retrieve glist containing NvDsUserMeta objects
    while l_user is not None:
        try:
            # Note that l_user.data needs a cast to pyds.NvDsUserMeta
            # The casting is done by pyds.NvDsUserMeta.cast()
            # The casting also keeps ownership of the underlying memory
            # in the C code, so the Python garbage collector will leave it alone
            user_meta = pyds.NvDsUserMeta.cast(l_user.data)
        except StopIteration:
            break
        
        # Check data type of user_meta - our custom camera metadata type
        if user_meta and user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type(b"NVIDIA.NVDS_GST_META_CAMERA_INFO"):
            #print(f"DEBUG: 🎯 Found NVDS_GST_META_CAMERA_INFO in NvDsUserMeta")
            
            # NVIDIA OFFICIAL APPROACH: Use Python bindings (like NvDsPastFrameObjBatch.cast())
            try:
                # Note that user_meta.user_meta_data needs a cast to pyds.CameraInfoMeta
                # The casting is done by pyds.CameraInfoMeta.cast()
                # The casting also keeps ownership of the underlying memory
                # in the C code, so the Python garbage collector will leave it alone
                camera_meta = pyds.CameraInfoMeta.cast(user_meta.user_meta_data)
                
                if camera_meta:
                    # Extract data using official Python bindings
                    camera_id = camera_meta.camera_id if camera_meta.camera_id else None
                    camera_name = camera_meta.camera_name if camera_meta.camera_name else None
                    camera_url = camera_meta.camera_url if camera_meta.camera_url else None
                    source_id = camera_meta.source_id
                    
                    # Update camera_info
                    camera_info['camera_id'] = camera_id
                    camera_info['camera_name'] = camera_name
                    camera_info['camera_url'] = camera_url
                    camera_info['source_id'] = source_id
                    camera_info['nvds_user_meta_found'] = True
                    
                    #print(f"DEBUG: ✅ SUCCESS - Extracted camera data using OFFICIAL Python bindings!")
                    #print(f"DEBUG:   camera_id='{camera_id}', camera_name='{camera_name}'")
                    #print(f"DEBUG:   source_id={source_id}")
                    break
                else:
                    print(f"DEBUG: ⚠️ CameraInfoMeta.cast() returned None")
                    
            except Exception as e:
                print(f"DEBUG: ❌ Error using official Python bindings: {e}")
                print(f"DEBUG: 📋 Note: Make sure PyDS is compiled with CameraInfoMeta bindings")
                # Mark that we found the metadata type but couldn't access data
                camera_info['nvds_user_meta_found'] = True
                camera_info['access_error'] = str(e)
                break
            
        try:
            l_user = l_user.next
        except StopIteration:
            break
    
    return camera_info

def nvanalytics_src_pad_buffer_probe(pad, info, u_data):
    """
    Enhanced probe function that extracts both analytics data and camera metadata.
    This demonstrates accessing camera_id and source_id after nvdsanalytics plugin.
    """
    frame_number = 0
    num_rects = 0
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return

    # Retrieve batch metadata from the gst_buffer
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list

    while l_frame:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        frame_number = frame_meta.frame_num
        l_obj = frame_meta.obj_meta_list
        num_rects = frame_meta.num_obj_meta
        
        # Extract camera metadata for this frame
        camera_info = get_camera_metadata_from_frame(frame_meta)
        
        obj_counter = {
            PGIE_CLASS_ID_VEHICLE: 0,
            PGIE_CLASS_ID_PERSON: 0,
            PGIE_CLASS_ID_BICYCLE: 0,
            PGIE_CLASS_ID_ROADSIGN: 0
        }
        
        print("#" * 60)
        print(f"=== FRAME PROCESSING ===")
        print(f"Camera ID: {camera_info['camera_id']}")
        print(f"Source ID: {camera_info['source_id']}")
        print(f"Camera Name: {camera_info['camera_name']}")
        print(f"Camera URL: {camera_info['camera_url']}")
        print(f"Frame Number: {frame_number}")
        print("#" * 60)
        
        while l_obj:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
            except StopIteration:
                break
            
            obj_counter[obj_meta.class_id] += 1
            l_user_meta = obj_meta.obj_user_meta_list
            
            # Extract object level analytics metadata
            while l_user_meta:
                try:
                    user_meta = pyds.NvDsUserMeta.cast(l_user_meta.data)
                    if user_meta.base_meta.meta_type == pyds.NvDsMetaType.NVDS_OBJ_META_NVDSANALYTICS:
                        user_meta_data = pyds.NvDsAnalyticsObjInfo.cast(user_meta.user_meta_data)
                        
                        # Enhanced logging with camera information
                        if user_meta_data.dirStatus:
                            print(f"[Camera: {camera_info['camera_id']}] Object {obj_meta.object_id} moving in direction: {user_meta_data.dirStatus}")
                        if user_meta_data.lcStatus:
                            print(f"[Camera: {camera_info['camera_id']}] Object {obj_meta.object_id} line crossing status: {user_meta_data.lcStatus}")
                        if user_meta_data.ocStatus:
                            print(f"[Camera: {camera_info['camera_id']}] Object {obj_meta.object_id} overcrowding status: {user_meta_data.ocStatus}")
                        if user_meta_data.roiStatus:
                            print(f"[Camera: {camera_info['camera_id']}] Object {obj_meta.object_id} roi status: {user_meta_data.roiStatus}")
                            
                except StopIteration:
                    break

                try:
                    l_user_meta = l_user_meta.next
                except StopIteration:
                    break
                    
            try:
                l_obj = l_obj.next
            except StopIteration:
                break

        # Get frame level analytics metadata
        l_user = frame_meta.frame_user_meta_list
        while l_user:
            try:
                user_meta = pyds.NvDsUserMeta.cast(l_user.data)
                if user_meta.base_meta.meta_type == pyds.NvDsMetaType.NVDS_FRAME_META_NVDSANALYTICS:
                    user_meta_data = pyds.NvDsAnalyticsFrameMeta.cast(user_meta.user_meta_data)
                    
                    # Enhanced frame analytics logging with camera information
                    if user_meta_data.objInROIcnt:
                        print(f"[Camera: {camera_info['camera_id']}] Objects in ROI: {user_meta_data.objInROIcnt}")
                    if user_meta_data.objLCCumCnt:
                        print(f"[Camera: {camera_info['camera_id']}] Line crossing Cumulative: {user_meta_data.objLCCumCnt}")
                    if user_meta_data.objLCCurrCnt:
                        print(f"[Camera: {camera_info['camera_id']}] Line crossing Current Frame: {user_meta_data.objLCCurrCnt}")
                    if user_meta_data.ocStatus:
                        print(f"[Camera: {camera_info['camera_id']}] Overcrowding status: {user_meta_data.ocStatus}")
                        
            except StopIteration:
                break
            try:
                l_user = l_user.next
            except StopIteration:
                break

        print(f"[Camera: {camera_info['camera_id']}] Frame={frame_number}, Stream ID={frame_meta.pad_index}, Objects={num_rects}, Vehicles={obj_counter[PGIE_CLASS_ID_VEHICLE]}, Persons={obj_counter[PGIE_CLASS_ID_PERSON]}")
        
        try:
            l_frame = l_frame.next
        except StopIteration:
            break
        print("#" * 60)

    return Gst.PadProbeReturn.OK

def main(args):
    """
    Main function using nvmultiurisrcbin with REST API only.
    Sources can only be added via REST API, not at startup.
    """
    # Always start with empty pipeline - sources added only via REST API
    max_batch_size = 8  # Maximum number of sources that can be added
    
    platform_info = PlatformInfo()
    # Standard GStreamer initialization
    Gst.init(None)

    # Create gstreamer elements
    print("Creating Pipeline")
    pipeline = Gst.Pipeline()
    if not pipeline:
        sys.stderr.write("Unable to create Pipeline\n")

    print("Creating nvmultiurisrcbin")
    # Create nvmultiurisrcbin - this replaces nvstreammux + multiple nvurisrcbin
    multiurisrcbin = Gst.ElementFactory.make("nvmultiurisrcbin", "multi-uri-source")
    if not multiurisrcbin:
        sys.stderr.write("Unable to create nvmultiurisrcbin\n")
        sys.exit(1)

    # Configure nvmultiurisrcbin properties
    multiurisrcbin.set_property("batched-push-timeout", MUXER_BATCH_TIMEOUT_USEC)
    multiurisrcbin.set_property("width", MUXER_OUTPUT_WIDTH)
    multiurisrcbin.set_property("height", MUXER_OUTPUT_HEIGHT)
    multiurisrcbin.set_property("live-source", True)
    multiurisrcbin.set_property("max-batch-size", max_batch_size)
    multiurisrcbin.set_property("drop-pipeline-eos", False)  
    multiurisrcbin.set_property("async-handling", True)
    
    # Configure REST API
    multiurisrcbin.set_property("ip-address", REST_API_IP)
    multiurisrcbin.set_property("port", int(REST_API_PORT))
    
    # No initial sources - all sources must be added via REST API
    print("Pipeline configured for REST API only - no initial sources")

    pipeline.add(multiurisrcbin)

    # Create processing elements
    print("Creating processing elements")
    
    # Queues for better pipeline flow
    queue1 = Gst.ElementFactory.make("queue", "queue1")
    queue2 = Gst.ElementFactory.make("queue", "queue2")
    queue3 = Gst.ElementFactory.make("queue", "queue3")
    queue4 = Gst.ElementFactory.make("queue", "queue4")
    queue5 = Gst.ElementFactory.make("queue", "queue5")
    queue6 = Gst.ElementFactory.make("queue", "queue6")
    queue7 = Gst.ElementFactory.make("queue", "queue7")

    # Primary inference
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    if not pgie:
        sys.stderr.write("Unable to create pgie\n")

    # Tracker
    tracker = Gst.ElementFactory.make("nvtracker", "tracker")
    if not tracker:
        sys.stderr.write("Unable to create tracker\n")

    # Analytics - this is where we'll add our probe to access camera metadata
    nvanalytics = Gst.ElementFactory.make("nvdsanalytics", "analytics")
    if not nvanalytics:
        sys.stderr.write("Unable to create nvanalytics\n")
    nvanalytics.set_property("config-file", "config_nvdsanalytics.txt")

    # Tiler
    tiler = Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
    if not tiler:
        sys.stderr.write("Unable to create tiler\n")

    # Video converter
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    if not nvvidconv:
        sys.stderr.write("Unable to create nvvidconv\n")

    # OSD
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")
    if not nvosd:
        sys.stderr.write("Unable to create nvosd\n")
    nvosd.set_property('process-mode', OSD_PROCESS_MODE)
    nvosd.set_property('display-text', OSD_DISPLAY_TEXT)

    # Sink
    if platform_info.is_integrated_gpu():
        print("Creating nv3dsink")
        sink = Gst.ElementFactory.make("nv3dsink", "nv3d-sink")
    else:
        if platform_info.is_platform_aarch64():
            print("Creating nv3dsink")
            sink = Gst.ElementFactory.make("nv3dsink", "nv3d-sink")
        else:
            print("Creating EGLSink")
            sink = Gst.ElementFactory.make("nveglglessink", "nvvideo-renderer")
    
    if not sink:
        sys.stderr.write("Unable to create sink\n")

    # Configure elements
    pgie.set_property('config-file-path', "dsnvanalytics_pgie_config.txt")
    pgie.set_property("batch-size", max_batch_size)
    
    # Configure tiler for maximum batch size
    tiler.set_property("rows", 1)
    tiler.set_property("columns", 1)
    tiler.set_property("width", TILED_OUTPUT_WIDTH)
    tiler.set_property("height", TILED_OUTPUT_HEIGHT)
    tiler.set_property("square-seq-grid", 1)
    sink.set_property("qos", 0)
    sink.set_property("async", False)
    sink.set_property("max-lateness", -1)
    sink.set_property("qos", False)
    sink.set_property("sync", False)
 

    # Set tracker properties
    config = configparser.ConfigParser()
    config.read('dsnvanalytics_tracker_config.txt')
    config.sections()

    for key in config['tracker']:
        if key == 'tracker-width':
            tracker_width = config.getint('tracker', key)
            tracker.set_property('tracker-width', tracker_width)
        if key == 'tracker-height':
            tracker_height = config.getint('tracker', key)
            tracker.set_property('tracker-height', tracker_height)
        if key == 'gpu-id':
            tracker_gpu_id = config.getint('tracker', key)
            tracker.set_property('gpu_id', tracker_gpu_id)
        if key == 'll-lib-file':
            tracker_ll_lib_file = config.get('tracker', key)
            tracker.set_property('ll-lib-file', tracker_ll_lib_file)
        if key == 'll-config-file':
            tracker_ll_config_file = config.get('tracker', key)
            tracker.set_property('ll-config-file', tracker_ll_config_file)

    print("Adding elements to Pipeline")
    pipeline.add(queue1)
    pipeline.add(queue2)
    pipeline.add(queue3)
    pipeline.add(queue4)
    pipeline.add(queue5)
    pipeline.add(queue6)
    pipeline.add(queue7)
    pipeline.add(pgie)
    pipeline.add(tracker)
    pipeline.add(nvanalytics)
    pipeline.add(tiler)
    pipeline.add(nvvidconv)
    pipeline.add(nvosd)
    pipeline.add(sink)

    # Link elements in the pipeline
    # nvmultiurisrcbin -> queue1 -> pgie -> queue2 -> tracker -> queue3 -> 
    # nvdsanalytics -> queue4 -> tiler -> queue5 -> nvvideoconvert -> 
    # queue6 -> nvdsosd -> queue7 -> sink
    print("Linking elements in the Pipeline")
    multiurisrcbin.link(queue1)
    queue1.link(pgie)
    pgie.link(queue2)
    queue2.link(tracker)
    tracker.link(queue3)
    queue3.link(nvanalytics)
    nvanalytics.link(queue4)
    queue4.link(tiler)
    tiler.link(queue5)
    queue5.link(nvvidconv)
    nvvidconv.link(queue6)
    queue6.link(nvosd)
    nvosd.link(queue7)
    queue7.link(sink)

    # Create event loop and feed gstreamer bus messages to it
    loop = GLib.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)
    
    # Add probe to nvanalytics src pad to access camera metadata after analytics
    nvanalytics_src_pad = nvanalytics.get_static_pad("src")
    if not nvanalytics_src_pad:
        sys.stderr.write("Unable to get nvanalytics src pad\n")
    else:
        nvanalytics_src_pad.add_probe(Gst.PadProbeType.BUFFER, nvanalytics_src_pad_buffer_probe, 0)

    # Print startup information
    print("\n" + "="*80)
    print("DeepStream nvdsanalytics with nvmultiurisrcbin")
    print("REST API ONLY - No initial sources")
    print("="*80)
    print(f"REST API Server: http://{REST_API_IP}:{REST_API_PORT}")
    print(f"Max Batch Size: {max_batch_size}")
    print("\nAll sources must be added via REST API:")
    print("curl -X POST http://localhost:9000/api/v1/streams \\")
    print("  -H \"Content-Type: application/json\" \\")
    print("  -d '{")
    print("    \"camera_id\": \"camera_001\",")
    print("    \"camera_url\": \"rtsp://192.168.1.100:554/stream\",")
    print("    \"camera_name\": \"Main Entrance\"")
    print("  }'")
    print("\nTo remove sources:")
    print("curl -X POST http://localhost:9000/api/v1/streams \\")
    print("  -H \"Content-Type: application/json\" \\")
    print("  -d '{")
    print("    \"camera_id\": \"camera_001\",")
    print("    \"camera_url\": \"rtsp://192.168.1.100:554/stream\",")
    print("    \"change\": \"remove\"")
    print("  }'")
    print("="*80)

    print("Starting pipeline")
    # Start pipeline
    pipeline.set_state(Gst.State.PLAYING)
    
    try:
        loop.run()
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
    
    # Cleanup
    print("Exiting app")
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    sys.exit(main(sys.argv))


