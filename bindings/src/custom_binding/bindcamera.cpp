#include "bind_string_property_definitions.h"
#include "include/bindcamera.hpp"

namespace py = pybind11;

namespace pydeepstream {

    // callback function to copy camera metadata to another destination
    gpointer copy_camera_meta(gpointer data, gpointer user_data) {
        NvDsUserMeta *user_meta = (NvDsUserMeta *) data;
        CameraInfoMeta *srcData = (CameraInfoMeta *) user_meta->user_meta_data;
        CameraInfoMeta *dstData = (CameraInfoMeta *) g_malloc0(sizeof(CameraInfoMeta));
        
        if (srcData && dstData) {
            // Copy the entire structure safely
            memcpy(dstData, srcData, sizeof(CameraInfoMeta));
        }
        
        return (gpointer) dstData;
    }

    // callback function to release camera metadata
    void release_camera_meta(gpointer data, gpointer user_data) {
        NvDsUserMeta *user_meta = (NvDsUserMeta *) data;
        if (user_meta->user_meta_data) {
            g_free(user_meta->user_meta_data);
            user_meta->user_meta_data = NULL;
        }
    }

    void bindcamera(py::module &m) {
        /* CameraInfoMeta bindings to be used with NvDsUserMeta */
        py::class_<CameraInfoMeta>(m, "CameraInfoMeta",
                        pydsdoc::custom::CameraInfoMetaDoc::descr)
        .def(py::init<>())
        // binding camera_id string with CameraInfoMeta char array
        .def_property("camera_id", 
                     [](CameraInfoMeta &self) { return std::string(self.camera_id); },
                     [](CameraInfoMeta &self, const std::string &val) { 
                         strncpy(self.camera_id, val.c_str(), sizeof(self.camera_id) - 1);
                         self.camera_id[sizeof(self.camera_id) - 1] = '\0';
                     })
        // binding source_id uint with CameraInfoMeta uint
        .def_readwrite("source_id", &CameraInfoMeta::source_id)
        // binding camera_name string with CameraInfoMeta char array
        .def_property("camera_name",
                     [](CameraInfoMeta &self) { return std::string(self.camera_name); },
                     [](CameraInfoMeta &self, const std::string &val) { 
                         strncpy(self.camera_name, val.c_str(), sizeof(self.camera_name) - 1);
                         self.camera_name[sizeof(self.camera_name) - 1] = '\0';
                     })
        // binding camera_url string with CameraInfoMeta char array
        .def_property("camera_url",
                     [](CameraInfoMeta &self) { return std::string(self.camera_url); },
                     [](CameraInfoMeta &self, const std::string &val) { 
                         strncpy(self.camera_url, val.c_str(), sizeof(self.camera_url) - 1);
                         self.camera_url[sizeof(self.camera_url) - 1] = '\0';
                     })

        // binding function to cast user_meta_data to CameraInfoMeta
        .def("cast",
             [](void *data) {
                 return (CameraInfoMeta *) data;
             },
             py::return_value_policy::reference,
             pydsdoc::custom::CameraInfoMetaDoc::cast);

        // binding function used to allocate memory for CameraInfoMeta in C
        // Memory ownership is maintained by bindings and only reference is passed to Python
        m.def("alloc_camera_meta",
              [](NvDsUserMeta *meta) {
                  auto *mem = (CameraInfoMeta *) g_malloc0(sizeof(CameraInfoMeta));
                  meta->base_meta.copy_func = (NvDsMetaCopyFunc) pydeepstream::copy_camera_meta;
                  meta->base_meta.release_func = (NvDsMetaReleaseFunc) pydeepstream::release_camera_meta;
                  return mem;
              },
              py::return_value_policy::reference,
              pydsdoc::methodsDoc::alloc_camera_meta);
    }
}
