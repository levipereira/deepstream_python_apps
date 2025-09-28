#!/bin/bash

# API Configuration
API_BASE="http://localhost:9000/api/v1/stream"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Show help
show_help() {
    echo -e "${BLUE}=== Stream Manager ===${NC}"
    echo
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo
    echo -e "${YELLOW}Commands:${NC}"
    echo "  add     - Add a new camera source"
    echo "  remove  - Remove camera source"
    echo "  list    - List all camera IDs"
    echo "  help    - Show this help"
    echo
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 add uniqueSensorID_H264"
    echo "  $0 add uniqueSensorID_H265" 
    echo "  $0 remove uniqueSensorID_H264"
    echo "  $0 list"
}

# Add H264 source
add_h264_source() {
    local camera_id="$1"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    
    local json_payload=$(cat <<EOF
{
  "key": "sensor",
  "value": {
      "camera_id": "$camera_id",
      "camera_name": "front_door",
      "camera_url": "file:///opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h264.mp4",
      "change": "camera_add",
      "metadata": {
          "resolution": "1920 x1080",
          "codec": "h264",
          "framerate": 30
      }
  },
  "headers": {
      "source": "vst",
      "created_at": "$timestamp"
  }
}
EOF
)
    
    echo -e "${BLUE}Adding H264 camera: $camera_id${NC}"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/add" \
        -H "Content-Type: application/json" \
        -d "$json_payload")
    
    local http_code=$(echo "$response" | tail -n1)
    
    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        echo -e "${GREEN}✓ Camera added successfully${NC}"
    else
        echo -e "${RED}✗ Failed to add camera (HTTP $http_code)${NC}"
        return 1
    fi
}

# Add H265 source  
add_h265_source() {
    local camera_id="$1"
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    
    local json_payload=$(cat <<EOF
{
  "key": "sensor",
  "value": {
      "camera_id": "$camera_id",
      "camera_name": "front_door",
      "camera_url": "file:///opt/nvidia/deepstream/deepstream/samples/streams/sample_1080p_h265.mp4",
      "change": "camera_add",
      "metadata": {
          "resolution": "1920 x1080",
          "codec": "h265",
          "framerate": 30
      }
  },
  "headers": {
      "source": "vst",
      "created_at": "$timestamp"
  }
}
EOF
)
    
    echo -e "${BLUE}Adding H265 camera: $camera_id${NC}"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/add" \
        -H "Content-Type: application/json" \
        -d "$json_payload")
    
    local http_code=$(echo "$response" | tail -n1)
    
    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "201" ]]; then
        echo -e "${GREEN}✓ Camera added successfully${NC}"
    else
        echo -e "${RED}✗ Failed to add camera (HTTP $http_code)${NC}"
        return 1
    fi
}

# Add source (auto-detect H264/H265 based on ID)
add_source() {
    local camera_id="$1"
    
    if [[ -z "$camera_id" ]]; then
        echo -e "${RED}Error: Camera ID required${NC}"
        echo "Usage: $0 add CAMERA_ID"
        return 1
    fi
    
    # Auto-detect codec based on ID
    if [[ "$camera_id" == *"H265"* ]]; then
        add_h265_source "$camera_id"
    else
        add_h264_source "$camera_id"
    fi
}

# Remove source
remove_source() {
    local camera_id="$1"
    
    if [[ -z "$camera_id" ]]; then
        echo -e "${RED}Error: Camera ID required${NC}"
        echo "Usage: $0 remove CAMERA_ID"
        return 1
    fi
    
    local timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")
    
    local json_payload=$(cat <<EOF
{
  "key": "sensor",
  "value": {
      "camera_id": "$camera_id",
      "change": "camera_remove"
  },
  "headers": {
      "source": "vst",
      "created_at": "$timestamp"
  }
}
EOF
)
    
    echo -e "${BLUE}Removing camera: $camera_id${NC}"
    
    local response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE/remove" \
        -H "Content-Type: application/json" \
        -d "$json_payload")
    
    local http_code=$(echo "$response" | tail -n1)
    
    if [[ "$http_code" == "200" ]] || [[ "$http_code" == "204" ]]; then
        echo -e "${GREEN}✓ Camera removed successfully${NC}"
    else
        echo -e "${RED}✗ Failed to remove camera (HTTP $http_code)${NC}"
        return 1
    fi
}

# List camera IDs
list_cameras() {
    echo -e "${BLUE}Available camera operations:${NC}"
    echo
    echo -e "${YELLOW}H264 Cameras:${NC}"
    echo "  uniqueSensorID_H264"
    echo
    echo -e "${YELLOW}H265 Cameras:${NC}"  
    echo "  uniqueSensorID_H265"
    echo
    echo "Use: $0 add CAMERA_ID"
    echo "Use: $0 remove CAMERA_ID"
}

# Main function
main() {
    if [[ $# -eq 0 ]]; then
        show_help
        exit 0
    fi
    
    case "$1" in
        add)
            add_source "$2"
            ;;
        remove)
            remove_source "$2"
            ;;
        list)
            list_cameras
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# Check if curl is available
if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl not found. Please install curl.${NC}"
    exit 1
fi

# Execute main function
main "$@"
