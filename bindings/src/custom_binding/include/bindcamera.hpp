#pragma once

#include "pyds.hpp"
#include "camera_meta.hpp" // Include the actual C++ header file for CameraInfoMeta
// We add bindcamera.cpp related docstring in customdoc.h
// And any functions related to our custom bindings would go in
// functionsdoc.h docstring file
#include "../../../docstrings/customdoc.h"
#include "../../../docstrings/functionsdoc.h"

namespace py = pybind11;

namespace pydeepstream {
    void bindcamera(py::module &m); // Declare the bindings function for this submodule
}
