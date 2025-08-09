# Frame2IMG — Video Frame Extractor

A simple, modern, dark-themed desktop app to extract frames from a video and save them as images.
Built with Python, CustomTkinter for UI, and OpenCV for video processing.

## Features

- Dark-themed GUI using CustomTkinter
- Select input video and output folder
- Shows total frame count (when available)
- Start/Cancel extraction (keeps UI responsive)
- Progress bar (determinate if total frames are known, indeterminate otherwise)
- PNG-only output (lossless)
- Open output folder from the UI after extraction
- Filename prefix for saved files (default: `frame_`, or input video filename if left blank)
- Option to skip existing files (merge with previous runs, auto-increments zero-padding digits to 6 for safer naming)
- Configurable zero-padding digits
- Top-right “?” About button with View License

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
3. Optionally set:
   - "Prefix": text prepended to filenames (invalid characters are sanitized).
   - "Skip existing": do not overwrite if a file with the same name exists.
   - "Digits": number of zero-padding digits for filenames (1–12). Defaults to 5 (or 6 if invalid and Skip existing is enabled).
4. Click "Start Processing". You can cancel anytime.
5. When finished (or if partially completed), use "Open Output Folder" to view saved frames.

Notes:

- If total frames are unknown, the app uses an indeterminate progress bar.
- The default naming is `frame_00000.png`. You can change the `Prefix`.
- When "Skip existing" is enabled, filenames use the original frame index to keep names stable across multiple runs.
- Hover over "Skip existing" to see a short tooltip explaining the behavior.
- If Prefix is left blank, it will default to the input video filename (sanitized) plus an underscore.
- If `cv2.imwrite` fails (e.g., disk full), a clear error is shown and processing stops.
- Be mindful of disk space when extracting frames, especially for large videos.

## Packaging (Optional)

A PyInstaller spec file (`FrameExtractor.spec`) is present. To build an executable (output name will be `Frame2IMG.exe`):

```bash
pyinstaller FrameExtractor.spec
```

Optional polish (already wired in the spec):

- App icon (Windows): place `icon.ico` in the project root. The spec auto-detects and embeds it.
- Version metadata: edit `file_version.txt` (provided) with your details. The spec auto-detects and embeds it.
- Bump the in-app version by updating `__version__` in `frame_extractor_app.py` (it appears in the window title).

Then rebuild with:

```bash
pyinstaller FrameExtractor.spec
```

Tip: If you change only the icon or version file, you can delete the `build/` and `dist/` folders before rebuilding to ensure a clean build.

## Troubleshooting

- OpenCV errors: Ensure `opencv-python` installed correctly and the video codec is supported.
- Permission errors: Choose an output folder you can write to (the app also tests writability before starting).
- Large videos: Extracting every frame may use significant disk space; consider using external tools to compress or downscale images if needed.
