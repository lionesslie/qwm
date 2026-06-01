#!/usr/bin/env bash
# debug.sh - Launch QWM in a nested Xephyr session for testing

set -e

# Configuration
SCREEN_SIZE="1280x720"
DISPLAY_NUM=":100"

echo "=> Starting Xephyr on display $DISPLAY_NUM with size $SCREEN_SIZE"
Xephyr $DISPLAY_NUM -ac -screen $SCREEN_SIZE -br -reset -terminate &
XEPHYR_PID=$!

# Wait for Xephyr to start
sleep 1

echo "=> Starting QWM inside Xephyr"
DISPLAY=$DISPLAY_NUM python3 -m qwm.main --debug &
QWM_PID=$!

echo "=> QWM running. Press Ctrl+C to exit."

# Wait for QWM to exit, then kill Xephyr
wait $QWM_PID
kill $XEPHYR_PID
