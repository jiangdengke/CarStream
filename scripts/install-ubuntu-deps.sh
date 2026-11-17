#!/usr/bin/env bash
set -euo pipefail

# Run deliberately on the Ubuntu board. Never run this script as part of sync.
sudo apt-get update
sudo apt-get install -y \
  python3-venv python3-pip python3-gi python3-gst-1.0 \
  gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-gst-plugins-bad-1.0 \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-nice

printf '%s\n' 'Existing Rockchip MPP packages are retained; no camera network configuration is changed.'
printf '%s\n' 'On non-Rockchip test machines, x264enc and avdec_h264 need plugins-ugly and libav.'
