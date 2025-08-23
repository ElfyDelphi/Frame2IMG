# Frame2Image

A minimal, modern dark-themed GUI to extract every frame from a video into highest-quality PNG images.

## Features
- Highest quality, lossless PNG output (no resizing or quality loss)
- Simple UI: choose input video and output folder, then Start
- Progress bar, live status, and Cancel
- Exact frame counting via ffprobe when available; falls back to an estimate otherwise
- Auto GPU detection and acceleration via NVDEC (when supported); CPU fallback otherwise
- Output saved inside `<video_name>_frames/` subfolder
- Cross-platform Qt (PySide6) GUI

## Requirements
- Python 3.9+
- Linux/macOS/Windows

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
- Click Start. You can Cancel anytime and open the output folder with the folder button.

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

- `assets/screenshots/main.png` (main window)
- `assets/screenshots/demo.gif` (short extraction demo)

## GPU acceleration (optional)
- This app will automatically use FFmpeg with CUDA/NVDEC (GPU) to decode video if available, then save frames as lossless PNG.
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

## Supported formats
- Containers: MP4, MOV, AVI, MKV, WEBM, M4V, MPG/MPEG, WMV
- Codecs: H.264/AVC, H.265/HEVC, VP9, and others supported by your FFmpeg/OpenCV build
- Output: PNG (lossless). JPEG support is planned.

## Non‑Goals (initial public release)
- Full video editing/transcoding or audio extraction
- Scene detection and per‑scene export (future exploration)
- Batch/multi‑file queueing (planned)
- macOS packaging (help wanted)

## Roadmap
- Optional JPEG output and quality control
- Batch mode / multiple input files
- Simple scene‑based frame sampling
- macOS packaging and notarization

## Contributing
See `CONTRIBUTING.md` for setup and guidelines.

## License and third‑party
- Project license: MIT (see `LICENSE`)
- FFmpeg/ffprobe are licensed separately (LGPL/GPL depending on build). This app uses your system FFmpeg/ffprobe when available. If you distribute binaries in the future, include FFmpeg’s license files and notices.

## Windows quick start (Python)

Run from source on Windows (no EXE build required):

```bat
py -3.11 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
py app.py
```

Optional: verify FFmpeg hardware acceleration support:

```bat
ffmpeg -hide_banner -hwaccels
```
You should see `cuda` or `nvdec` for NVIDIA GPU decode. If not, the app will use CPU and the GPU badge will show "GPU: CPU".
