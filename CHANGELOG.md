# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
- No changes yet.

## [v0.1.1] - 2025-08-22
### Added
- UI: "Open output folder" button (enabled after run) and optional "Open folder when done" checkbox.
- Persistence: remembers last used input video, output folder, start/end times, and options via `QSettings`.
- UI: "Open input folder" button next to the video field.
- Window: remembers window size and position (geometry) via `QSettings`.
- Title: display app version in the window title.

### Changed
- Windows helper script now uses `py -3` for version flexibility.
- README: Windows quick start updated; added macOS quick start snippet.
- Docs refinements for Python-only distribution.

### Fixed
- Tooltip text visibility in dark theme (tooltips were showing as blank on hover).

### Removed
- (From previous cleanup) Packaging artifacts: `Frame2Image.spec`, `tools/pack_win.ps1`, `tools/pack_win.bat`, `third_party/ffmpeg/`.
- `.gitignore` rules for `third_party/ffmpeg/bin` binaries.

## [v0.1.0] - 2025-08-22
### Added
- Minimal, modern dark-themed GUI using PySide6
- Extract every frame to lossless PNG in `<video_name>_frames/`
- Progress bar, live status, cancel support
- GPU decode via NVDEC/CUDA when available; CPU fallback otherwise
- Exact frame counting using ffprobe when available; OpenCV fallback
- Windows build scripts (`tools/pack_win.*`) and `Frame2Image.spec`
- Optional bundling of `ffmpeg.exe` and `ffprobe.exe` from `third_party/ffmpeg/bin/`
- Basic CI workflow (syntax check) and GitHub issue/PR templates

### Fixed
- Robust shutdown and thread cleanup to avoid `QThread` deletion errors on app close

### Docs
- README with setup, GPU notes, Windows build, supported formats, non-goals, roadmap
- OSS files: `LICENSE` (MIT), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`

[v0.1.0]: https://github.com/ElfyDelphi/Frame2Image/releases/tag/v0.1.0
[v0.1.1]: https://github.com/ElfyDelphi/Frame2Image/releases/tag/v0.1.1
