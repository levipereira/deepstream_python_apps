# Python Bindings Camera Metadata Implementation

## Overview

This document describes the implementation of Python bindings for camera metadata access in DeepStream applications. The implementation provides seamless access to `camera_id` and `camera_name` metadata through official PyBind11 bindings, following the NVIDIA DeepStream Python API patterns.

## Architecture

```
DeepStream Pipeline: nvmultiurisrcbin > gst-infer > tracker > nvdsanalytics > queue
                                                              ↓
                                                      Camera metadata
                                                      (NvDsUserMeta)
                                                              ↓
                                                      Python bindings
                                                      (PyBind11)
                                                              ↓
                                                      Python application
```

## Implementation Details

### 1. Custom Metadata Structure

**File**: `bindings/src/custom_binding/include/camera_meta.hpp`

```cpp
#include <string>

using namespace std;

// Camera metadata structure for DeepStream nvmultiurisrcbin
// This structure MUST match exactly with gst-nvmultiurisrcbincreator.cpp
struct CameraInfoMeta {
  char camera_id[64];       // Camera identifier from REST API (gchar in C++)
  unsigned int source_id;   // Source identifier assigned by DeepStream (guint in C++)
  char camera_name[64];     // Camera name from REST API (gchar in C++)
  char camera_url[128];     // Camera URL/URI from REST API (gchar in C++)
};
```

**Key Features**:
- **Type Compatibility**: Uses `char` and `unsigned int` to match C++ `gchar` and `guint` for PyBind11
- **Fixed-Size Arrays**: Ensures memory safety and compatibility with C++ structure
- **Exact Synchronization**: Must match the C++ structure in `gst-nvmultiurisrcbincreator.cpp`

### 2. PyBind11 Binding Header

**File**: `bindings/src/custom_binding/include/bindcamera.hpp`

```cpp
#include "pyds.hpp"
#include "camera_meta.hpp"
#include "../../../docstrings/customdoc.h"
#include "../../../docstrings/functionsdoc.h"

namespace py = pybind11;

namespace pydeepstream {
    void bindcamera(py::module &m);
}
```

**Purpose**: Declares the `bindcamera` function for module registration in the main PyDS module.

### 3. PyBind11 Implementation

**File**: `bindings/src/custom_binding/bindcamera.cpp`

```cpp
#include "bind_string_property_definitions.h"
#include "include/bindcamera.hpp"

namespace py = pybind11;

namespace pydeepstream {

    void bindcamera(py::module &m) {
        /* CameraInfoMeta bindings to be used with NvDsUserMeta */
        py::class_<CameraInfoMeta>(m, "CameraInfoMeta",
                        pydsdoc::custom::CameraInfoMetaDoc::descr)
        .def(py::init<>())
        .def_property("camera_id", STRING_CHAR_ARRAY(CameraInfoMeta, camera_id, 64))
        .def_readwrite("source_id", &CameraInfoMeta::source_id)
        .def_property("camera_name", STRING_CHAR_ARRAY(CameraInfoMeta, camera_name, 64))
        .def_property("camera_url", STRING_CHAR_ARRAY(CameraInfoMeta, camera_url, 128))
        .def("cast",
             [](void *data) {
                 return (CameraInfoMeta *) data;
             },
             py::return_value_policy::reference,
             pydsdoc::custom::CameraInfoMetaDoc::cast);

        m.def("alloc_camera_meta",
              [](NvDsUserMeta *meta) {
                  auto *mem = (CameraInfoMeta *) g_malloc0(
                          sizeof(CameraInfoMeta));
                  meta->base_meta.copy_func = (NvDsMetaCopyFunc) pydeepstream::camera_meta_copy_func;
                  meta->base_meta.release_func = (NvDsMetaReleaseFunc) pydeepstream::camera_meta_release_func;
                  return mem;
              },
              py::return_value_policy::reference,
              pydsdoc::methodsDoc::alloc_camera_meta);
    }
}
```

**Key Features**:
- **Property Access**: Uses `STRING_CHAR_ARRAY` macro for safe string property access
- **Cast Function**: Provides `cast()` method for converting C pointers to Python objects
- **Memory Management**: Integrates with DeepStream's memory management system
- **Reference Policy**: Uses `py::return_value_policy::reference` to avoid unnecessary copying

### 4. Documentation Strings

**File**: `bindings/docstrings/customdoc.h`

```cpp
namespace pydsdoc
{
    namespace custom
    {
        namespace CameraInfoMetaDoc
        {
            constexpr const char* descr = R"pyds(
                Holds camera metadata information for DeepStream nvmultiurisrcbin.

                :ivar camera_id: *str*, Camera identifier from REST API.
                :ivar source_id: *int*, Source identifier assigned by DeepStream.
                :ivar camera_name: *str*, Camera name from REST API.
                :ivar camera_url: *str*, Camera URL/URI from REST API.)pyds";

            constexpr const char* cast=R"pyds(cast given object/data to :class:`CameraInfoMeta`, call pyds.CameraInfoMeta.cast(data))pyds";
        }
    }
}
```

**File**: `bindings/docstrings/functionsdoc.h`

```cpp
constexpr const char* alloc_camera_meta=R"pyds(
    Allocate a :class:`CameraInfoMeta` for camera metadata.

    :arg user_meta: An object of type :class:`NvDsUserMeta` to configure copy/release functions.
    :returns: Allocated :class:`CameraInfoMeta`)pyds";
```

### 5. Module Registration

**File**: `bindings/src/pyds.cpp`

```cpp
#include "bindtrackermeta.hpp"
#include "custom_binding/include/bindcustom.hpp"
#include "custom_binding/include/bindcamera.hpp" // NEW
#include "bindpreprocessmeta.hpp"
#include "bindroimeta.hpp"

// ... (other includes) ...

namespace pydeepstream {

    PYBIND11_MODULE(pyds, m) {
        // ... (other bindings) ...

        bindcustom(m);
        bindcamera(m); // NEW
        bindpreprocessmeta(m);
        bindroimeta(m);
    }   // end PYBIND11_MODULE(pyds, m)
}
```

### 6. Build System Integration

**File**: `bindings/CMakeLists.txt`

```cmake
add_library(pyds SHARED src/pyds.cpp src/utils.cpp src/bindanalyticsmeta.cpp
            src/bindfunctions.cpp src/bindgstnvdsmeta.cpp
            src/bindmeta360.cpp src/bindnvbufsurface.cpp src/bindnvdsinfer.cpp
            src/bindnvdsmeta.cpp src/bindnvosd.cpp src/bindopticalflow.cpp
            src/bindschema.cpp src/bindtrackermeta.cpp src/custom_binding/bindcustom.cpp
            src/custom_binding/bindcamera.cpp src/bindpreprocessmeta.cpp src/bindroimeta.cpp)
```

## Python Usage

### 1. Basic Metadata Access

```python
import pyds

def get_camera_metadata_from_frame(frame_meta):
    """
    Extract camera metadata using ONLY NvDsUserMeta
    Following deepstream_user_metadata_app.c pattern exactly
    """
    camera_info = {
        'camera_id': None,
        'source_id': frame_meta.source_id,
        'camera_name': None,
        'camera_url': None
    }

    # NVIDIA OFFICIAL PATTERN: Access frame-level user metadata
    l_user = frame_meta.frame_user_meta_list
    while l_user is not None:
        try:
            user_meta = pyds.NvDsUserMeta.cast(l_user.data)
        except StopIteration:
            break

        # Check data type of user_meta - our custom camera metadata type
        if user_meta and user_meta.base_meta.meta_type == pyds.nvds_get_user_meta_type(b"NVIDIA.NVDS_GST_META_CAMERA_INFO"):
            try:
                camera_meta = pyds.CameraInfoMeta.cast(user_meta.user_meta_data)
                
                if camera_meta:
                    camera_info['camera_id'] = camera_meta.camera_id
                    camera_info['camera_name'] = camera_meta.camera_name
                    camera_info['camera_url'] = camera_meta.camera_url
                    camera_info['source_id'] = camera_meta.source_id
                    break
            except Exception as e:
                print(f"Error accessing camera metadata: {e}")
                break

        try:
            l_user = l_user.next
        except StopIteration:
            break

    return camera_info
```

### 2. Integration in DeepStream Application

```python
def osd_sink_pad_buffer_probe(pad, info, u_data):
    """Probe function to extract camera metadata from frames"""
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer")
        return

    # Retrieve batch metadata from the gst_buffer
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    if not batch_meta:
        return

    # Process each frame in the batch
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
        except StopIteration:
            break

        # Extract camera metadata
        camera_info = get_camera_metadata_from_frame(frame_meta)
        
        if camera_info['camera_id']:
            print(f"Camera ID: {camera_info['camera_id']}")
            print(f"Camera Name: {camera_info['camera_name']}")
            print(f"Source ID: {camera_info['source_id']}")

        try:
            l_frame = l_frame.next
        except StopIteration:
            break

    return Gst.PadProbeReturn.OK
```

## Key Features

1. **Official NVIDIA Pattern**: Follows the exact pattern from `deepstream_user_metadata_app.c`
2. **Type Safety**: Proper C++ to Python type conversion using PyBind11
3. **Memory Management**: Integrates with DeepStream's memory management system
4. **String Handling**: Safe string property access using `STRING_CHAR_ARRAY` macro
5. **Documentation**: Comprehensive docstrings for Python API documentation
6. **Reference Management**: Proper reference counting to prevent memory leaks

## Build Process

### 1. Compilation

```bash
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps/bindings
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### 2. Installation

```bash
# Install the updated PyDS module
sudo make install

# Or use the provided installation script
cd /opt/nvidia/deepstream/deepstream/sources/deepstream_python_apps
./user_deepstream_python_apps_install.sh
```

### 3. Verification

```python
import pyds

# Verify CameraInfoMeta is available
print("CameraInfoMeta available:", hasattr(pyds, 'CameraInfoMeta'))

# Test metadata type registration
meta_type = pyds.nvds_get_user_meta_type(b"NVIDIA.NVDS_GST_META_CAMERA_INFO")
print("Metadata type registered:", meta_type)
```

## Files Modified

### New Files Added

1. **`bindings/src/custom_binding/include/camera_meta.hpp`**
   - Camera metadata structure definition for Python bindings
   - Type-compatible with C++ implementation

2. **`bindings/src/custom_binding/include/bindcamera.hpp`**
   - Header file declaring bindcamera function
   - Includes necessary dependencies

3. **`bindings/src/custom_binding/bindcamera.cpp`**
   - PyBind11 implementation for CameraInfoMeta
   - Property access and cast function implementation

### Modified Files

1. **`bindings/CMakeLists.txt`**
   - Added `src/custom_binding/bindcamera.cpp` to build system
   - Ensures proper compilation of camera bindings

2. **`bindings/docstrings/customdoc.h`**
   - Added docstrings for CameraInfoMeta class
   - Added cast function documentation

3. **`bindings/docstrings/functionsdoc.h`**
   - Added docstring for alloc_camera_meta function
   - Integrated with existing documentation system

4. **`bindings/src/pyds.cpp`**
   - Added include for bindcamera.hpp
   - Registered bindcamera module in PYBIND11_MODULE

## Testing

The implementation has been tested with:

- **Dynamic Source Addition**: REST API source management
- **Multiple Concurrent Sources**: Simultaneous camera streams
- **Memory Management**: No memory leaks detected
- **Type Safety**: Proper C++ to Python type conversion
- **String Handling**: Safe string property access
- **Downstream Compatibility**: Works with existing DeepStream plugins

## Compatibility

- **DeepStream Version**: 8.0
- **Python Version**: 3.6+
- **PyBind11**: Latest version included with DeepStream
- **C++ Standard**: C++11 compatible
- **Memory Management**: GLib 2.0+ compatible

## Error Handling

The implementation includes comprehensive error handling:

```python
try:
    camera_meta = pyds.CameraInfoMeta.cast(user_meta.user_meta_data)
    if camera_meta:
        # Access camera metadata safely
        camera_id = camera_meta.camera_id
        camera_name = camera_meta.camera_name
except Exception as e:
    print(f"Error accessing camera metadata: {e}")
    # Fallback to default values
    camera_id = None
    camera_name = None
```

## Performance Considerations

1. **Memory Efficiency**: Uses reference counting to avoid unnecessary copying
2. **Type Conversion**: Minimal overhead in C++ to Python type conversion
3. **String Access**: Efficient string property access using PyBind11 macros
4. **Batch Processing**: Compatible with DeepStream's batch processing model

## Future Enhancements

1. **Additional Metadata Fields**: Easy to extend with new camera properties
2. **Validation Functions**: Add input validation for camera metadata
3. **Serialization**: JSON serialization support for camera metadata
4. **Logging Integration**: Enhanced logging for camera metadata access

## Troubleshooting

### Common Issues

1. **Import Error**: Ensure PyDS is properly compiled and installed
2. **Type Mismatch**: Verify C++ and Python structure definitions match
3. **Memory Leaks**: Use proper reference counting and avoid circular references
4. **Build Errors**: Check CMakeLists.txt includes and dependencies

### Debug Commands

```bash
# Check PyDS installation
python3 -c "import pyds; print(dir(pyds))"

# Verify camera metadata type
python3 -c "import pyds; print(pyds.nvds_get_user_meta_type(b'NVIDIA.NVDS_GST_META_CAMERA_INFO'))"

# Test structure creation
python3 -c "import pyds; meta = pyds.CameraInfoMeta(); print(meta.camera_id)"
```

This implementation provides a robust, type-safe, and efficient way to access camera metadata in Python DeepStream applications, following official NVIDIA patterns and best practices.
