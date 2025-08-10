# Frame2IMG — Video Frame Extractor

A simple, modern, dark-themed desktop app to extract frames from a video and save them as images.
Built with Python, CustomTkinter for UI, and FFmpeg for frame extraction.

## Features

- Minimal UI: Select one video and an output folder, then Start
- FFmpeg-only extraction for speed and display-accurate orientation
- Automatic orientation correction (honors rotation metadata)
- PNG-only output (lossless)
- Fixed naming: `frame_%05d.png` written directly into the chosen folder
- Overwrites existing files for the simplest flow
- Indeterminate progress bar and Cancel support
- Open output folder from the UI after extraction
- About dialog with License and Third‑party licenses viewer

## Requirements

- Python 3.8+
- Windows/macOS/Linux

Install dependencies:

```bash
pip install -r requirements.txt
```

Windows (PowerShell) quick start:

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -U pip wheel
pip install -r requirements.txt
python frame_extractor_app.py
```

If activation is blocked, temporarily allow scripts for this session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Run

```bash
python frame_extractor_app.py
```

## Usage

1. Click "Select Video" and choose a video file (mp4, mkv, webm, mov, avi, wmv, flv).
2. Click "Select Folder" and choose an output directory with write permissions.
3. Click "Start Processing". You can cancel anytime.
4. When finished, use "Open Output Folder" to view saved frames.

Notes:

- Autorotation: FFmpeg honors rotation metadata, so extracted frames match the player’s orientation.
- Naming: Files are saved as `frame_%05d.png` starting at 0 (overwrite is enabled).
- Progress: The bar is indeterminate since we don’t probe total frames.
- Disk space: Extracting every frame can use a lot of space on long/high‑res videos.
- Override: Set the `FFMPEG_PATH` environment variable to point to your own ffmpeg binary if you prefer it over the bundled one.

## Packaging (PyInstaller)

`FrameExtractor.spec` bundles the app as a single Windows EXE (`dist/Frame2IMG.exe`). If `bin/ffmpeg.exe` and `bin/ffprobe.exe` are present, they are included automatically. The Third‑party license notice (`licenses/FFmpeg-LGPL.txt`) is also included.

```bash
pyinstaller FrameExtractor.spec
```

Polish (already wired in the spec):

- App icon (Windows): place `icon.ico` in the project root.
- Version metadata: edit `file_version.txt`.
- Bump the in‑app version by updating `__version__` in `frame_extractor_app.py`.

Tip: For a clean rebuild, delete `build/` and `dist/` before running PyInstaller.

## Troubleshooting

- FFmpeg not found (running from source): ensure `bin/ffmpeg.exe` exists on Windows or `ffmpeg` is on your PATH.
- Permission errors: Choose an output folder you can write to (the app tests writability before starting).
- Large videos: Extracting every frame may use significant disk space; consider downscaling if needed.
