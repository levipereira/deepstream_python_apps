# DeepStream 8.0 Camera Info UserMeta Plugin - Usage Guide

This guide provides step-by-step instructions for installing and using the Camera Info UserMeta plugin that enables camera metadata attachment using `NvDsUserMeta` in the DeepStream `nvmultiurisrcbin` plugin.

## Overview

The Camera Info UserMeta plugin allows `camera_id` and `camera_name` to be available downstream after the `nvdsanalytics` plugin, following the official NVIDIA pattern from `deepstream_user_metadata_app.c`. This enables enhanced analytics capabilities with camera context throughout the DeepStream pipeline.

## Prerequisites

- NVIDIA DeepStream SDK 8.0 installed
- CUDA 12.8 or compatible version
- Ubuntu 22.04 LTS
- Git installed
- Python virtual environment support

## Installation Steps

### Step 1: Backup Original Library

First, backup the original `gstnvdscustomhelper` library:

```bash
mv /opt/nvidia/deepstream/deepstream-8.0/sources/libs/gstnvdscustomhelper/ /opt/nvidia/deepstream/deepstream-8.0/sources/libs/gstnvdscustomhelper.ori
```

### Step 2: Clone the Plugin Repository

Clone the repository with the specific feature branch:

```bash
cd /tmp
git clone -b feature/cameraInfo-UserMeta-downstream-support https://github.com/levipereira/deepstream_8.0_plugins.git
```

### Step 3: Install the Custom Library

Copy the custom library to the DeepStream installation:

```bash
cp -r deepstream_8.0_plugins/libs/gstnvdscustomhelper/ /opt/nvidia/deepstream/deepstream-8.0/sources/libs/
```

### Step 4: Build and Install the Library

Navigate to the library directory and build with CUDA support:

```bash
cd /opt/nvidia/deepstream/deepstream-8.0/sources/libs/gstnvdscustomhelper
CUDA_VER=12.8 make install
```

### Step 5: Install Python Bindings

Download and install the Python bindings for the camera info functionality:

```bash
cd /opt/nvidia/deepstream/deepstream-8.0
wget https://raw.githubusercontent.com/levipereira/deepstream_python_apps/refs/heads/feature/cameraInfo-UserMeta-downstream-support/user_deepstream_python_apps_install_camera_info.sh

chmod +x user_deepstream_python_apps_install_camera_info.sh

# Install additional dependencies
./user_additional_install.sh

# Install Python bindings with camera info support
./user_deepstream_python_apps_install_camera_info.sh --build-bindings -r feature/cameraInfo-UserMeta-downstream-support
```

## Usage Instructions

### Step 1: Navigate to the Analytics Application

```bash
cd /opt/nvidia/deepstream/deepstream-8.0/sources/deepstream_python_apps/apps/deepstream-nvdsanalytics
```

### Step 2: Activate Python Virtual Environment

**Important**: You must use the `pyds` virtual environment to run the test:

```bash
source /opt/nvidia/deepstream/deepstream-8.0/sources/deepstream_python_apps/pyds/bin/activate
```

### Step 3: Run the Camera Info Analytics Application

```bash
python3 deepstream_nvdsanalytics_camerainfo.py
```

### Step 4: Add Camera Streams (Separate Terminal Session)

In a **new terminal session**, navigate to the application directory and use the stream manager:

```bash
cd /opt/nvidia/deepstream/deepstream-8.0/sources/deepstream_python_apps/apps/deepstream-nvdsanalytics
./stream_manager.sh
```

#### Stream Manager Commands

The stream manager provides the following commands:

```bash
=== Stream Manager ===

Usage: ./stream_manager.sh [COMMAND] [OPTIONS]

Commands:
  add     - Add a new camera source
  remove  - Remove camera source
  list    - List all camera IDs
  help    - Show this help

Examples:
  ./stream_manager.sh add uniqueSensorID_H264
  ./stream_manager.sh add uniqueSensorID_H265
  ./stream_manager.sh remove uniqueSensorID_H264
  ./stream_manager.sh list
```

## Expected Output

When the application is running successfully, you should see output similar to the following in the logs:

```
############################################################
=== FRAME PROCESSING ===
Camera ID: uniqueSensorID_H264
Source ID: 0
Camera Name: front_door
Camera URL: file:///opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4
Frame Number: 1
############################################################
[Camera: uniqueSensorID_H264] Objects in ROI: {'RF': 0}
[Camera: uniqueSensorID_H264] Line crossing Cumulative: {'Exit': 0}
[Camera: uniqueSensorID_H264] Line crossing Current Frame: {'Exit': 0}
[Camera: uniqueSensorID_H264] Frame=1, Stream ID=0, Objects=0, Vehicles=0, Persons=0
############################################################
############################################################
=== FRAME PROCESSING ===
Camera ID: uniqueSensorID_H264
Source ID: 0
Camera Name: front_door
Camera URL: file:///opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4
Frame Number: 2
############################################################
[Camera: uniqueSensorID_H264] Objects in ROI: {'RF': 0}
[Camera: uniqueSensorID_H264] Line crossing Cumulative: {'Exit': 0}
[Camera: uniqueSensorID_H264] Line crossing Current Frame: {'Exit': 0}
[Camera: uniqueSensorID_H264] Frame=2, Stream ID=0, Objects=0, Vehicles=0, Persons=0
############################################################
```

## Key Features Demonstrated

The output shows that the plugin successfully provides:

1. **Camera ID**: Unique identifier for each camera (`uniqueSensorID_H264`)
2. **Camera Name**: Human-readable camera name (`front_door`)
3. **Source ID**: Internal source identifier (`0`)
4. **Camera URL**: Source stream location
5. **Frame Processing**: Real-time frame analysis with camera context
6. **Analytics Integration**: ROI and line crossing detection with camera-specific data

## Troubleshooting

### Common Issues

1. **Virtual Environment**: Ensure you're using the `pyds` virtual environment
2. **CUDA Version**: Verify CUDA version compatibility (12.8 recommended)
3. **Permissions**: Ensure proper permissions for DeepStream installation directory
4. **Dependencies**: Make sure all Python dependencies are installed

### Verification Steps

1. Check if the custom library was installed correctly:
   ```bash
   ls -la /opt/nvidia/deepstream/deepstream-8.0/sources/libs/gstnvdscustomhelper/
   ```

2. Verify Python bindings installation:
   ```bash
   source /opt/nvidia/deepstream/deepstream-8.0/sources/deepstream_python_apps/pyds/bin/activate
   python3 -c "import pyds; print('PyDS imported successfully')"
   ```

## Additional Resources

- [Implementation Documentation](https://github.com/levipereira/deepstream_8.0_plugins/blob/feature/cameraInfo-UserMeta-downstream-support/libs/gstnvdscustomhelper/camera_info_usermeta_implementation.md)
- [DeepStream Python Apps Repository](https://github.com/levipereira/deepstream_python_apps/tree/feature/cameraInfo-UserMeta-downstream-support)
- [NVIDIA DeepStream Documentation](https://docs.nvidia.com/metropolis/deepstream/dev-guide/)

## Support

For issues and questions regarding this plugin implementation, please refer to the documentation within the feature branch or create an issue in the repository.

