# Contributing to Frame2Image

Thanks for your interest in contributing! This project aims to be a simple, high‑quality frame extractor with clear scope.

## Ways to contribute
- Report bugs and edge cases (crashes, unsupported inputs)
- Suggest small features that align with scope (see README Non‑Goals)
- Improve docs and packaging (Windows builds, GPU notes)

## Development setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Commit and PR guidelines
- Use clear commit messages, e.g. `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`
- Keep PRs focused and small when possible; link to an issue
- Include screenshots for UI changes

## Code style
- Python 3.9+
- Prefer type hints and clear error messages
- Keep UI responsive; long work must run off the main thread (see `FrameExtractorWorker` in `app.py`)

## Packaging (Windows)
- See `tools/pack_win.ps1` / `tools/pack_win.bat`
- Optional: place `ffmpeg.exe` and `ffprobe.exe` under `third_party/ffmpeg/bin/` before building to bundle them

Thanks again!
