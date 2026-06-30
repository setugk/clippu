#!/bin/sh
# Promote journery:latest (already built by deploy-beta) to prod instances.
# Does NOT rebuild — just recreates containers from the existing image.
set -e

recreate() {
  NAME=$1 PORT=$2 DATA=$3 JNAME=$4
  echo "Recreating $NAME..."
  docker stop "$NAME" 2>/dev/null || true
  docker rm   "$NAME" 2>/dev/null || true
  docker run -d \
    --name "$NAME" \
    --restart unless-stopped \
    -p "$PORT:5000" \
    -v "$DATA:/data" \
    -e "JOURNERY_NAME=$JNAME" \
    journery:latest
  echo "Started: $NAME"
}

recreate clipboard        5050 /volume1/docker/clipboard/data        Setu
recreate clipboard-agrams 5051 /volume1/docker/clipboard-agrams/data Apoo

echo "All prod instances updated."
