# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Changed
- Docs updated for Python-only distribution (no Windows EXE build by default).
- README: "Windows quick start (Python)" replaces packaging instructions.
- CONTRIBUTING: removed packaging section; added Windows Python run instructions.

### Removed
- Packaging artifacts: `Frame2Image.spec`, `tools/pack_win.ps1`, `tools/pack_win.bat`, `third_party/ffmpeg/`.
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
