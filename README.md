# Frame2Image

A minimal, modern dark-themed GUI to extract every frame from a video into highest-quality PNG images.

> Note: This project targets Linux only and is Python-based. Windows and macOS are not supported in this release.

## Features
- Highest quality, lossless PNG output (no resizing or quality loss)
- Simple UI: choose input video and output folder, then Start
- Progress bar, live status, and Cancel
- Asynchronous video preview with seek slider and time readout (non-blocking UI)
- Exact frame counting via ffprobe when available; falls back to an estimate otherwise
- Auto GPU detection and acceleration via NVDEC (when supported); CPU fallback otherwise
- Output saved inside `<video_name>_frames/` subfolder
- Optional: "Open folder when done" to automatically open the output directory after extraction
- Remembers last used input video and output folder
- "Open input folder" button next to the video field
- Remembers window size and position
- Version shown in the window title
 - PNG or JPEG output (JPEG quality adjustable)

## Requirements
- Python 3.9+
- Linux

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
python app.py
```

## Usage
- Select a video file and an output folder.
- Optional: set Start/End times to extract only a segment.
- Optional: enable "Precision frame count (slower)" for exact counts via ffprobe.
- Optional: enable "Open folder when done" to auto-open the output directory when finished.
- Click Start. You can Cancel anytime. Use the folder button next to the input to open its containing folder, and the folder button in the controls to open the output. The app remembers your last used paths and window size.

### Asynchronous video preview
- Live, non-blocking preview with a seek slider and current/total time display.
- Works even for long videos by decoding frames in a background thread.
- Uses OpenCV for preview decoding. If a frame cannot be shown, the last good frame remains visible and a brief message is displayed.
- The preview window respects Start/End times, letting you scrub only within the selected range.

### Time range extraction
- Formats accepted: `HH:MM:SS(.ms)`, `MM:SS(.ms)`, or plain seconds.
- End must be greater than Start. If duration is known, values are clamped to the video length.

### Precision frame count
- Uses `ffprobe -count_frames` for exact counts; may be slow on long videos.
- When off, the app uses `nb_frames` (if present) or estimates via duration×fps, with OpenCV fallback.

### GPU badge
- "GPU: NVDEC" means FFmpeg with NVDEC/CUDA will be used for decoding.
- "GPU: CPU" means GPU decode is unavailable; OpenCV CPU path will be used.

## Screenshots
Coming soon. You can place screenshots here and they will render on GitHub:

![Main Window](assets/screenshots/main.png)
![Demo](assets/screenshots/demo.gif)

- `assets/screenshots/main.png` (main window)
- `assets/screenshots/demo.gif` (short extraction demo)

## GPU acceleration (optional)
- This app will automatically use FFmpeg with CUDA/NVDEC (GPU) to decode video if available, then save frames as lossless PNG or JPEG.
- If FFmpeg with CUDA is not found, it falls back to CPU decoding via OpenCV.

### Enable/check FFmpeg CUDA
1) Install FFmpeg (Linux example):
```bash
sudo apt-get install ffmpeg
```
2) Verify hardware accel support:
```bash
ffmpeg -hide_banner -hwaccels
```
You should see `cuda` or `nvdec` listed. If not, your FFmpeg build may lack CUDA; the app will still work using CPU.

## Notes
- PNGs are lossless; compression level does not affect visual quality. This app uses PNG to preserve maximum quality.
- If a video fails to open, your system codecs may be missing. Installing FFmpeg or using a different video file can help.
- Very long/high‑resolution videos will generate many large files; ensure you have sufficient disk space.

## Troubleshooting
- Preview shows "Preview unavailable": The codec/container may not be supported by your OpenCV build. Install/upgrade FFmpeg and OpenCV, or try another file. The extraction path may still work via FFmpeg.
- GPU badge shows "GPU: CPU": Your FFmpeg build likely lacks CUDA/NVDEC. Run `ffmpeg -hide_banner -hwaccels` to verify. The app will still work on CPU.
- Exact frame count is slow: Uncheck "Precision frame count (slower)" or keep it off for long videos.
- ffprobe not found: Install FFmpeg so metadata and precision counting work. The app falls back to estimates when missing.
- Cancel takes a moment: The app cancels workers and waits briefly for threads/processes to exit cleanly.

## Logging and diagnostics
- The app emits lightweight logs at INFO level to stdout/stderr (module logger `frame2image`).
- To temporarily enable DEBUG logs for deeper diagnostics, edit `app.py` and change `logging.basicConfig(level=logging.INFO, ...)` to `DEBUG`, then run the app. Revert when done to reduce verbosity.
- Logs include key lifecycle events: metadata loading, preview worker start/errors, extraction start/fallbacks, cancellation, and application close/cleanup.

## Supported formats
- Containers: MP4, MOV, AVI, MKV, WEBM, M4V, MPG/MPEG, WMV
- Codecs: H.264/AVC, H.265/HEVC, VP9, and others supported by your FFmpeg/OpenCV build
- Output: PNG (lossless) and JPEG (quality adjustable).

## Non‑Goals (initial public release)
- Full video editing/transcoding or audio extraction
- Scene detection and per‑scene export (future exploration)
- Batch/multi‑file queueing (planned)


## Roadmap
- Batch mode / multiple input files
- Simple scene‑based frame sampling


## Contributing
See `CONTRIBUTING.md` for setup and guidelines.

## License and third‑party
- Project license: MIT (see `LICENSE`)
- FFmpeg/ffprobe are licensed separately (LGPL/GPL depending on build). This app uses your system FFmpeg/ffprobe when available. If you distribute binaries in the future, include FFmpeg’s license files and notices.


