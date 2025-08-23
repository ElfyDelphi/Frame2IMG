# Requires: Windows 11 with Python installed
# Usage (PowerShell):
#   Set-ExecutionPolicy -Scope Process Bypass -Force
#   ./tools/pack_win.ps1

$ErrorActionPreference = 'Stop'
$PSStyle.OutputRendering = 'Ansi'

# Move to repo root
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $repoRoot

function Resolve-Python {
    try {
        $pyExe = (Get-Command py -ErrorAction Stop)
        # Prefer 3.11, fallback to latest 3.x
        try { return 'py -3.11' } catch { return 'py -3' }
    } catch {
        return 'python'
    }
}

$python = Resolve-Python
Write-Host "Using Python launcher: $python" -ForegroundColor Cyan

# Install deps
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip install "pyinstaller>=6.5,<7.0"

# Check ffmpeg/ffprobe presence
$ffmpeg = Test-Path "third_party/ffmpeg/bin/ffmpeg.exe"
$ffprobe = Test-Path "third_party/ffmpeg/bin/ffprobe.exe"
if (-not $ffmpeg) {
    Write-Warning "Optional: Place ffmpeg.exe under third_party/ffmpeg/bin/ to bundle it."
}
if (-not $ffprobe) {
    Write-Warning "Optional: Place ffprobe.exe under third_party/ffmpeg/bin/ to enable advanced metadata/precision counting."
}

# Build
& $python -m PyInstaller "Frame2Image.spec" --noconfirm

$exePath = Join-Path $repoRoot "dist/Frame2Image/Frame2Image.exe"
if (Test-Path $exePath) {
    Write-Host "Build complete:" -ForegroundColor Green
    Write-Host "  $exePath"
    Write-Host "You can zip the dist/Frame2Image folder for distribution."
} else {
    Write-Error "Build did not produce expected output at $exePath"
}
