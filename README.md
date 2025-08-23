# Frame2Image

A minimal, modern dark-themed GUI to extract every frame from a video into highest-quality PNG images.

## Features
- Highest quality, lossless PNG output (no resizing or quality loss)
- Simple UI: choose input video and output folder, then Start
- Progress bar, live status, and Cancel
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

## Windows 11 build (PyInstaller)

You must build on Windows (PyInstaller does not cross‑compile).

### Quick start
- PowerShell:
  ```powershell
  Set-ExecutionPolicy -Scope Process Bypass -Force
  .\tools\pack_win.ps1
  ```
- CMD:
  ```bat
  tools\pack_win.bat
  ```

This produces `dist/Frame2Image/Frame2Image.exe`.

### Manual steps (alternative)
```bat
py -3.11 -m pip install -r requirements.txt
py -3.11 -m pip install pyinstaller
py -3.11 -m PyInstaller Frame2Image.spec --noconfirm
```

### Bundling FFmpeg/FFprobe (optional but recommended)
- Place the following files under `third_party/ffmpeg/bin/` BEFORE building:
  - `ffmpeg.exe`
  - `ffprobe.exe` (enables advanced metadata and precision frame counting)
  - Any required `.dll` dependencies shipped with your FFmpeg build
- For GPU decoding on RTX GPUs (NVDEC/CUDA), use an FFmpeg build with NVDEC enabled (e.g., Gyan.dev "full" or BtbN win64 builds).
- Keep accompanying LICENSE/README files in `third_party/ffmpeg/` for license compliance.

### Verify GPU acceleration
Run in a Windows terminal:
```bat
ffmpeg -hide_banner -hwaccels
```
You should see `cuda` or `nvdec`. If not, the app will fall back to CPU and the GPU badge will show "GPU: CPU".

### Troubleshooting
- SmartScreen warning: click "More info" > "Run anyway" (unsigned build).
- Missing GPU badge or slow decode: ensure your FFmpeg build includes NVDEC and that NVIDIA drivers are up to date.
- Exact total frames not shown: make sure `ffprobe.exe` is present under `third_party/ffmpeg/bin/`.
