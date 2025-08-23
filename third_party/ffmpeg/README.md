# FFmpeg bundling for Frame2Image

Put your Windows FFmpeg build here if you want it bundled with the EXE.

Structure:

- third_party/ffmpeg/
  - bin/
    - ffmpeg.exe    # REQUIRED (if bundling)
    - ffprobe.exe   # OPTIONAL but recommended (bundled if present)
  - LICENSE(.txt|.md)  # OPTIONAL but recommended (license compliance)
  - README(.txt|.md)   # OPTIONAL
  - COPYING / COPYRIGHT (if present)

Build (PowerShell):

```
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --clean --noconfirm Frame2Image.spec
```

Notes:

- GPU/NVDEC: Use an FFmpeg build with CUDA/NVDEC enabled. Verify with:
  `ffmpeg -hide_banner -hwaccels` (should list `cuda` or `nvdec`).
- Licensing: When redistributing with FFmpeg, include FFmpeg license/readme files. The spec copies common license files to `licenses/ffmpeg` in the build if present here.
- Detection order (current app): Bundled FFmpeg is preferred first (inside onefile extraction dir or next to the EXE), and system PATH is used as a fallback.
- Frame counting: If `ffprobe.exe` is bundled here, the app uses it to get an exact `nb_frames` when available, or an accurate estimate via `duration * fps`. If not bundled, it falls back to OpenCV's `CAP_PROP_FRAME_COUNT`.
