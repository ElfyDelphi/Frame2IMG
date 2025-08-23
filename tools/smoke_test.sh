#!/usr/bin/env bash
# Frame2Image smoke-test helper
# This script launches the app, captures logs, and guides you through
# interactive steps, verifying expected log lines after each action.

set -u

# Move to project root (script is in tools/)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.." || exit 1

LOG_FILE="run.log"
: > "$LOG_FILE"

echo "=== Frame2Image Smoke Test ==="
echo "Project: $(pwd)"
echo "Log file: $LOG_FILE"

# Launch app in background and capture logs
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. Please install Python 3.9+ and rerun." >&2
  exit 1
fi

echo "Starting app... (leave the UI window open)"
# shellcheck disable=SC2002
python3 app.py 2>&1 | tee "$LOG_FILE" &
APP_PID=$!

echo "App PID: $APP_PID"

cleanup() {
  echo
  echo "Stopping app (if still running)..."
  if kill -0 "$APP_PID" >/dev/null 2>&1; then
    kill "$APP_PID" >/dev/null 2>&1 || true
    # Give it a moment to stop
    sleep 1
  fi
}
trap cleanup EXIT

prompt() {
  local msg="$1"
  echo
  echo "---"
  echo "$msg"
  read -r -p "Press Enter to continue..." _
}

check() {
  local desc="$1"; shift
  local pattern="$1"; shift
  echo "[Check] $desc"
  if grep -nE "$pattern" "$LOG_FILE" >/dev/null 2>&1; then
    grep -nE "$pattern" "$LOG_FILE" | tail -n 3
  else
    echo "  -> Not found yet"
  fi
}

# A) Preview smoke test
prompt "A1) In the app UI, click the video button and select a small MP4 (H.264)."
check "Metadata loaded" "Loaded metadata for"
check "Preview worker started" "Preview worker started"
check "Preview errors (if any)" "Preview error"

prompt "A2) Scrub the preview slider and resize the window to confirm responsiveness."
check "Preview errors (if any)" "Preview error"

# B) Time-range preview
prompt "B1) Enter Start=00:00:02 and End=00:00:06, then scrub within that range."
check "Preview errors (if any)" "Preview error"

# C) Extraction start and cancel
prompt "C1) Choose an output folder, then click Start to begin extraction."
check "Extraction started" "Start extraction:"

prompt "C2) After progress begins, click Cancel in the UI."
check "User cancel requested" "Cancel requested by user"
check "Worker cancel requested" "Worker cancel requested"
check "Canceled finish" "Extraction finished: success=False canceled=True"

# D) Extraction complete (no cancel)
prompt "D1) Click Start again and let extraction run to completion (do not cancel)."
check "Successful finish" "Extraction finished: success=True canceled=False"

# E) GPU verification
prompt "E1) Observe the GPU badge in the UI (NVDEC vs CPU). Press Enter to run FFmpeg hwaccels check."
if command -v ffmpeg >/dev/null 2>&1; then
  echo
  echo "FFmpeg hardware accelerations:"
  ffmpeg -hide_banner -hwaccels | sed 's/^/  /'
  echo
  echo "GPU-related log lines (if any, during extraction):"
  check "GPU/NVDEC mentions" "NVDEC|cuda|ffmpeg.*-hwaccel|-hwaccel_device"
else
  echo "ffmpeg not found on PATH; skipping hwaccels check."
fi

# F) Close during various states
prompt "F1) Close the app window now to verify shutdown and cleanup logs."
# Give the app a moment to write final logs
sleep 1
check "Close started" "Main window closing; starting cleanup"
check "Preview resources closed (if preview was running)" "Preview resources closed"
check "App closed" "Cleanup finished; app closed"

# End
echo
echo "=== Smoke test complete ==="
echo "Log file saved at $LOG_FILE"
exit 0
