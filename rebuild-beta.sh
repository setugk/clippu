#!/bin/sh
# Build journery:latest and start/restart clipboard-beta on port 5052.
set -e
cd /volume1/docker/journery-build

echo "Building journery:latest..."
docker build -t journery:latest . || { echo "Build failed"; exit 1; }

echo "Recreating clipboard-beta..."
docker stop clipboard-beta 2>/dev/null || true
docker rm   clipboard-beta 2>/dev/null || true
mkdir -p /volume1/docker/clipboard-beta/data
docker run -d \
  --name clipboard-beta \
  --restart unless-stopped \
  -p 5052:5000 \
  -v /volume1/docker/clipboard-beta/data:/data \
  -e "JOURNERY_NAME=Beta" \
  journery:latest

echo "Started: clipboard-beta → http://10.0.0.10:5052"
