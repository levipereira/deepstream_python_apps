#pragma once

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
