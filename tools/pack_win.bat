@echo off
setlocal

REM Change to repo root
cd /d %~dp0\..

REM Pick Python launcher
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  set "PY=py -3"
) else (
  set "PY=python"
)

echo Using Python launcher: %PY%

%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
%PY% -m pip install "pyinstaller>=6.5,<7.0"

if not exist third_party\ffmpeg\bin\ffmpeg.exe (
  echo [WARN] Optional: place ffmpeg.exe under third_party\ffmpeg\bin\ to bundle it.
)
if not exist third_party\ffmpeg\bin\ffprobe.exe (
  echo [WARN] Optional: place ffprobe.exe under third_party\ffmpeg\bin\ to enable advanced metadata/precision counting.
)

%PY% -m PyInstaller Frame2Image.spec --noconfirm

if exist dist\Frame2Image\Frame2Image.exe (
  echo Build complete: dist\Frame2Image\Frame2Image.exe
) else (
  echo Build failed: EXE not found.
  exit /b 1
)

endlocal
