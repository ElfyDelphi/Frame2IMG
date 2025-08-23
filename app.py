import os
import sys
import traceback
from pathlib import Path
from typing import Optional
import shutil
import subprocess
import json
import time

import cv2
from PySide6 import QtCore, QtGui, QtWidgets


# -------------------------
# Probe helpers (ffprobe)
# -------------------------
def _ffprobe_path() -> Optional[str]:
    """Locate ffprobe, preferring bundled copies over system PATH."""
    try:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cand = Path(meipass) / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
            if cand.exists():
                return str(cand)
    except Exception:
        pass
    try:
        exe_dir = Path(sys.executable).parent
        cand = exe_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if cand.exists():
            return str(cand)
    except Exception:
        pass
    try:
        script_dir = Path(__file__).resolve().parent
        cand = script_dir / ("ffprobe.exe" if os.name == "nt" else "ffprobe")
        if cand.exists():
            return str(cand)
    except Exception:
        pass
    p = shutil.which("ffprobe")
    if p:
        return p
    return None


def _parse_fraction(frac: str) -> Optional[float]:
    try:
        if not frac or frac.upper() == "N/A":
            return None
        if "/" in frac:
            n, d = frac.split("/", 1)
            n = float(n)
            d = float(d)
            if d == 0:
                return None
            return n / d
        # plain number
        return float(frac)
    except Exception:
        return None


def probe_total_frames_with_ffprobe(video_path: str) -> tuple[int, bool]:
    """Return (frames, exact) using ffprobe when available.
    exact=True when coming from nb_frames; otherwise an approximation via duration*fps.
    """
    fp = _ffprobe_path()
    if not fp:
        return 0, False
    try:
        cmd = [
            fp,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=nb_frames,avg_frame_rate,r_frame_rate:format=duration",
            "-of", "json",
            video_path,
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(out.stdout or "{}")
        streams = data.get("streams", [])
        fmt = data.get("format", {})
        nb_frames_val = None
        if streams:
            nb_frames_val = streams[0].get("nb_frames")
            avg_fr = _parse_fraction(streams[0].get("avg_frame_rate"))
            r_fr = _parse_fraction(streams[0].get("r_frame_rate"))
        else:
            avg_fr = None
            r_fr = None
        # Prefer exact nb_frames when numeric
        try:
            if nb_frames_val not in (None, "N/A"):
                frames = int(nb_frames_val)
                if frames > 0:
                    return frames, True
        except Exception:
            pass
        # Approximate via duration * fps
        dur_s = None
        try:
            d = fmt.get("duration")
            if d and d != "N/A":
                dur_s = float(d)
        except Exception:
            dur_s = None
        fps = avg_fr or r_fr
        if dur_s and fps and fps > 0:
            frames = int(round(dur_s * fps))
            if frames > 0:
                return frames, False
    except Exception:
        pass
    return 0, False


# -------------------------
# Additional probe helpers and time parsing
# -------------------------
def probe_video_metadata_with_ffprobe(video_path: str) -> dict:
    """Return metadata dict using ffprobe when available.
    Keys: frames, frames_exact, duration, fps, width, height, codec
    Missing values will be None/0.
    """
    meta = {
        "frames": 0,
        "frames_exact": False,
        "duration": None,
        "fps": None,
        "width": None,
        "height": None,
        "codec": None,
    }
    fp = _ffprobe_path()
    if not fp:
        return meta
    try:
        cmd = [
            fp,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries",
            "stream=nb_frames,avg_frame_rate,r_frame_rate,width,height,codec_name:format=duration",
            "-of", "json",
            video_path,
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(out.stdout or "{}")
        streams = data.get("streams", [])
        fmt = data.get("format", {})

        if streams:
            s0 = streams[0]
            # Frames
            nb_frames_val = s0.get("nb_frames")
            try:
                if nb_frames_val not in (None, "N/A"):
                    meta["frames"] = int(nb_frames_val)
                    if meta["frames"] > 0:
                        meta["frames_exact"] = True
            except Exception:
                pass
            # FPS
            avg_fr = _parse_fraction(s0.get("avg_frame_rate"))
            r_fr = _parse_fraction(s0.get("r_frame_rate"))
            meta["fps"] = avg_fr or r_fr
            # Geometry
            try:
                meta["width"] = int(s0.get("width")) if s0.get("width") else None
            except Exception:
                meta["width"] = None
            try:
                meta["height"] = int(s0.get("height")) if s0.get("height") else None
            except Exception:
                meta["height"] = None
            meta["codec"] = s0.get("codec_name")

        # Duration
        try:
            d = fmt.get("duration")
            if d and d != "N/A":
                meta["duration"] = float(d)
        except Exception:
            meta["duration"] = None

        # If frames unknown, approximate
        if not meta["frames"] and meta["duration"] and meta["fps"]:
            try:
                est = int(round(meta["duration"] * meta["fps"]))
                if est > 0:
                    meta["frames"] = est
                    meta["frames_exact"] = False
            except Exception:
                pass
    except Exception:
        pass
    return meta


def probe_total_frames_precise_ffprobe(video_path: str) -> int:
    """Use ffprobe -count_frames to get precise frame count when possible (can be slow)."""
    fp = _ffprobe_path()
    if not fp:
        return 0
    try:
        cmd = [
            fp,
            "-v", "error",
            "-count_frames",
            "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames",
            "-of", "json",
            video_path,
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(out.stdout or "{}")
        streams = data.get("streams", [])
        if streams:
            val = streams[0].get("nb_read_frames")
            try:
                frames = int(val)
                return frames if frames > 0 else 0
            except Exception:
                return 0
    except Exception:
        return 0
    return 0


def parse_time_to_seconds(s: Optional[str]) -> Optional[float]:
    """Parse 'HH:MM:SS(.ms)' or 'MM:SS(.ms)' or 'SS(.ms)' into seconds."""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    try:
        parts = s.split(":")
        parts = [p.strip() for p in parts]
        if len(parts) == 1:
            return float(parts[0])
        if len(parts) == 2:
            m = float(parts[0])
            sec = float(parts[1])
            return m * 60 + sec
        if len(parts) == 3:
            h = float(parts[0])
            m = float(parts[1])
            sec = float(parts[2])
            return h * 3600 + m * 60 + sec
    except Exception:
        return None
    return None


def format_seconds(secs: float) -> str:
    try:
        secs = max(0, int(round(secs)))
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        if h > 0:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:d}:{s:02d}"
    except Exception:
        return "--:--"


def _ffmpeg_path_global() -> Optional[str]:
    """Locate ffmpeg similarly to the worker method."""
    try:
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            cand = Path(meipass) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            if cand.exists():
                return str(cand)
    except Exception:
        pass
    try:
        exe_dir = Path(sys.executable).parent
        cand = exe_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if cand.exists():
            return str(cand)
    except Exception:
        pass
    try:
        script_dir = Path(__file__).resolve().parent
        cand = script_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
        if cand.exists():
            return str(cand)
    except Exception:
        pass
    p = shutil.which("ffmpeg")
    if p:
        return p
    return None


def ffmpeg_supports_cuda(ffmpeg_path: str) -> bool:
    try:
        out = subprocess.run([ffmpeg_path, "-hide_banner", "-hwaccels"], capture_output=True, text=True, check=True)
        txt = (out.stdout + out.stderr).lower()
        return ("cuda" in txt) or ("nvdec" in txt)
    except Exception:
        return False


# -------------------------
# Theming: Modern dark theme
# -------------------------
def apply_dark_theme(app: QtWidgets.QApplication) -> None:
    app.setStyle("Fusion")
    dark_palette = QtGui.QPalette()

    # Base colors
    dark_color = QtGui.QColor(45, 45, 45)
    disabled_color = QtGui.QColor(127, 127, 127)
    highlight_color = QtGui.QColor(53, 132, 228)  # blue accent

    dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(37, 37, 38))
    dark_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Base, dark_color)
    dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(60, 63, 65))
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.Text, disabled_color)
    dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(50, 50, 50))
    dark_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
    dark_palette.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, disabled_color)
    dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
    dark_palette.setColor(QtGui.QPalette.Highlight, highlight_color)
    dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.white)

    app.setPalette(dark_palette)

    # Subtle modern stylesheet
    app.setStyleSheet(
        """
        QWidget { font-size: 14px; }
        QLineEdit, QTextEdit, QPlainTextEdit { 
            background: #2d2d2d; color: #ffffff; border: 1px solid #3f3f3f; border-radius: 6px; padding: 6px; }
        QPushButton { 
            background: #3a3a3a; color: #ffffff; border: 1px solid #4a4a4a; border-radius: 6px; padding: 6px 10px; }
        QPushButton:hover { background: #444; }
        QPushButton:pressed { background: #2f2f2f; }
        QPushButton:disabled { color: #888; border-color: #3a3a3a; background: #2f2f2f; }
        QToolButton { 
            background: #3a3a3a; color: #ffffff; border: 1px solid #4a4a4a; border-radius: 6px; padding: 6px; }
        QToolButton:hover { background: #444; }
        QToolButton:pressed { background: #2f2f2f; }
        QToolButton:disabled { color: #888; border-color: #3a3a3a; background: #2f2f2f; }
        QProgressBar { border: 1px solid #3f3f3f; border-radius: 6px; text-align: center; }
        QProgressBar::chunk { background-color: #3584e4; }
        QGroupBox { border: 1px solid #3f3f3f; border-radius: 8px; margin-top: 12px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
        """
    )


# -------------------------
# Worker for frame extraction
# -------------------------
class FrameExtractorWorker(QtCore.QObject):
    progress = QtCore.Signal(int, int)  # current, total (total may be 0 if unknown)
    message = QtCore.Signal(str)
    finished = QtCore.Signal(bool, bool, str, int)  # success, canceled, out_dir, frames_saved
    error = QtCore.Signal(str)

    def __init__(self, video_path: str, output_folder: str, start_time: Optional[float] = None, end_time: Optional[float] = None, precision_count: bool = False):
        super().__init__()
        self.video_path = Path(video_path)
        self.output_folder = Path(output_folder)
        self._cancel = False
        self.start_time = start_time
        self.end_time = end_time
        self.precision_count = precision_count

    # --------- FFmpeg helpers ---------
    def _ffmpeg_path(self) -> Optional[str]:
        # Prefer bundled FFmpeg first, then fall back to system PATH
        # 1) PyInstaller onefile extraction dir
        try:
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                cand = Path(meipass) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
                if cand.exists():
                    return str(cand)
        except Exception:
            pass
        # 2) Next to the executable (onedir builds)
        try:
            exe_dir = Path(sys.executable).parent
            cand = exe_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            if cand.exists():
                return str(cand)
        except Exception:
            pass
        # 3) Next to the script (dev mode)
        try:
            script_dir = Path(__file__).resolve().parent
            cand = script_dir / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
            if cand.exists():
                return str(cand)
        except Exception:
            pass
        # 4) System PATH
        p = shutil.which("ffmpeg")
        if p:
            return p
        return None

    def _ffmpeg_supports_cuda(self, ffmpeg_path: str) -> bool:
        try:
            out = subprocess.run([ffmpeg_path, "-hide_banner", "-hwaccels"], capture_output=True, text=True, check=True)
            txt = (out.stdout + out.stderr).lower()
            return ("cuda" in txt) or ("nvdec" in txt)
        except Exception:
            return False

    def _run_ffmpeg_nvdec(self, ffmpeg_path: str, out_dir: Path, pad: int, total_frames: int, start_s: Optional[float], end_s: Optional[float]) -> int:
        """Run FFmpeg with NVDEC (CUDA) to dump frames to PNG. Returns frames_saved.
        Emits progress and respects cancellation.
        """
        # Ensure output dir exists
        out_dir.mkdir(parents=True, exist_ok=True)

        pattern = str(out_dir / f"frame_%0{pad}d.png")
        # Build seek args
        seek_args = []
        dur_args = []
        if start_s is not None and start_s > 0:
            seek_args += ["-ss", f"{start_s:.3f}"]
        if end_s is not None and (start_s is not None) and (end_s > start_s):
            dur = max(0.0, end_s - start_s)
            dur_args += ["-t", f"{dur:.3f}"]
        cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-y",
            "-hwaccel", "cuda",
            *seek_args,
            "-i", str(self.video_path),
            *dur_args,
            "-vsync", "0",
            "-start_number", "1",
            "-compression_level", "3",
            pattern,
            "-progress", "pipe:1",
            "-nostats",
            "-loglevel", "error",
        ]

        self.message.emit("Using FFmpeg (NVDEC) for GPU-accelerated decoding…")
        if total_frames > 0:
            self.progress.emit(0, total_frames)
        else:
            self.progress.emit(0, 0)

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        saved = 0
        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                if self._cancel:
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    break
                line = line.strip()
                if line.startswith("frame="):
                    try:
                        saved = int(line.split("=", 1)[1].strip())
                    except Exception:
                        continue
                    if total_frames > 0:
                        self.progress.emit(min(saved, total_frames), total_frames)
                    else:
                        self.progress.emit(saved, 0)
                elif line.startswith("progress=") and line.endswith("end"):
                    # FFmpeg reports completion
                    pass

            proc.wait()
            if self._cancel:
                # Determine how many files actually exist in case last frame count wasn't read
                try:
                    saved = sum(1 for _ in out_dir.glob("frame_*.png"))
                except Exception:
                    pass
                return saved

            if proc.returncode != 0:
                err = ""
                try:
                    if proc.stderr is not None:
                        err = proc.stderr.read()
                except Exception:
                    pass
                raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}).\n{err}")

            if saved == 0:
                # Fallback to counting files if 'frame=' wasn't seen
                try:
                    saved = sum(1 for _ in out_dir.glob("frame_*.png"))
                except Exception:
                    saved = 0
            return saved
        finally:
            try:
                if proc.stdout is not None:
                    proc.stdout.close()
            except Exception:
                pass
            try:
                if proc.stderr is not None:
                    proc.stderr.close()
            except Exception:
                pass

    @QtCore.Slot()
    def run(self) -> None:
        try:
            if not self.video_path.exists():
                raise FileNotFoundError(f"Video not found: {self.video_path}")

            # Probe metadata
            meta = probe_video_metadata_with_ffprobe(str(self.video_path))
            fps_val = meta.get("fps")
            # Total frames for whole video (prefer precision if requested)
            total_full = 0
            if self.precision_count:
                total_full = probe_total_frames_precise_ffprobe(str(self.video_path))
            if total_full <= 0:
                total_full = int(meta.get("frames") or 0)
            # Apply time range window to compute frames_in_range (approx if needed)
            start_s = self.start_time or 0.0
            end_s = self.end_time if (self.end_time is not None and (self.end_time > start_s)) else None
            frames_in_range = total_full
            if (self.start_time is not None or end_s is not None) and fps_val:
                try:
                    sf = int(max(0, round(start_s * fps_val)))
                    ef = int(round((end_s * fps_val))) if end_s is not None else total_full
                    if total_full > 0:
                        ef = min(ef, total_full)
                    frames_in_range = max(0, ef - sf)
                except Exception:
                    frames_in_range = 0
            # Fallback to OpenCV count if still unknown
            if frames_in_range is None or frames_in_range <= 0:
                cap_count = cv2.VideoCapture(str(self.video_path))
                if cap_count.isOpened():
                    try:
                        total_frames_cv = int(cap_count.get(cv2.CAP_PROP_FRAME_COUNT))
                        if total_frames_cv > 0:
                            if (self.start_time is not None or end_s is not None) and fps_val:
                                try:
                                    sf = int(max(0, round(start_s * fps_val)))
                                    ef = int(round((end_s * fps_val))) if end_s is not None else total_frames_cv
                                    frames_in_range = max(0, min(total_frames_cv, ef) - sf)
                                except Exception:
                                    frames_in_range = total_frames_cv
                            else:
                                frames_in_range = total_frames_cv
                        else:
                            frames_in_range = 0
                    finally:
                        cap_count.release()
                else:
                    frames_in_range = 0

            # Build output directory: <chosen_out>/<video_stem>_frames or unique suffix
            base_out = self.output_folder / f"{self.video_path.stem}_frames"
            out_dir = base_out
            idx_suffix = 1
            while out_dir.exists():
                # If exists and contains prior files, create a unique suffixed dir
                out_dir = base_out.parent / f"{base_out.name}_{idx_suffix}"
                idx_suffix += 1
            out_dir.mkdir(parents=True, exist_ok=True)

            # Filename padding
            pad = len(str(frames_in_range)) if frames_in_range and frames_in_range > 0 else 6

            # Prefer FFmpeg with NVDEC (CUDA) if available; fall back to OpenCV
            ffmpeg_path = self._ffmpeg_path()
            if ffmpeg_path and self._ffmpeg_supports_cuda(ffmpeg_path):
                try:
                    saved = self._run_ffmpeg_nvdec(ffmpeg_path, out_dir, pad, frames_in_range or 0, start_s if self.start_time else 0.0, end_s)
                    if self._cancel:
                        self.message.emit("Canceled by user.")
                        self.finished.emit(False, True, str(out_dir), saved)
                    else:
                        if frames_in_range and frames_in_range > 0:
                            self.progress.emit(min(saved, frames_in_range), frames_in_range)
                        self.message.emit("Done.")
                        self.finished.emit(True, False, str(out_dir), saved)
                    return
                except Exception as e_ff:
                    # Inform user and continue with CPU fallback
                    self.message.emit(f"FFmpeg GPU path failed, falling back to CPU (OpenCV)…\n{e_ff}")

            # ---------- OpenCV CPU fallback ----------
            cap = cv2.VideoCapture(str(self.video_path))
            if not cap.isOpened():
                raise RuntimeError("Failed to open video. Try installing codecs/FFmpeg or a different file.")

            # Seek to start time if specified
            if self.start_time and self.start_time > 0:
                try:
                    cap.set(cv2.CAP_PROP_POS_MSEC, self.start_time * 1000.0)
                except Exception:
                    pass

            png_params = [cv2.IMWRITE_PNG_COMPRESSION, 3]  # lossless; 0-9 only changes size/speed

            self.message.emit("Starting extraction…")
            if frames_in_range and frames_in_range > 0:
                self.progress.emit(0, frames_in_range)
            else:
                self.progress.emit(0, 0)

            saved = 0
            throttle = 10  # emit progress every N frames to reduce signal overhead
            fps_eff = None
            if not fps_val or fps_val <= 0:
                try:
                    fps_eff = cap.get(cv2.CAP_PROP_FPS)
                    if not fps_eff or fps_eff <= 0:
                        fps_eff = None
                except Exception:
                    fps_eff = None
            else:
                fps_eff = fps_val
            end_limit_frames = None
            end_limit_ms = None
            if self.end_time and (self.end_time > (self.start_time or 0)):
                if fps_eff:
                    try:
                        end_limit_frames = int(round((self.end_time - (self.start_time or 0)) * fps_eff))
                    except Exception:
                        end_limit_frames = None
                end_limit_ms = self.end_time * 1000.0

            while not self._cancel:
                ret, frame = cap.read()
                if not ret:
                    break
                saved += 1

                # Stop at end time if defined
                if end_limit_frames is not None and saved >= end_limit_frames:
                    break
                if end_limit_ms is not None:
                    try:
                        pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                        if pos_ms and pos_ms > end_limit_ms:
                            break
                    except Exception:
                        pass

                filename = out_dir / f"frame_{saved:0{pad}d}.png"
                ok = cv2.imwrite(str(filename), frame, png_params)
                if not ok:
                    raise RuntimeError(f"Failed to write frame to {filename}")

                if frames_in_range and frames_in_range > 0:
                    if saved % throttle == 0 or saved == frames_in_range:
                        self.progress.emit(saved, frames_in_range)
                else:
                    if saved % throttle == 0:
                        self.progress.emit(saved, 0)

            cap.release()

            if self._cancel:
                self.message.emit("Canceled by user.")
                self.finished.emit(False, True, str(out_dir), saved)
            else:
                # Final progress update
                if frames_in_range and frames_in_range > 0:
                    self.progress.emit(min(saved, frames_in_range), frames_in_range)
                self.message.emit("Done.")
                self.finished.emit(True, False, str(out_dir), saved)
        except Exception as e:
            # Best-effort cleanup of any OpenCV handles
            cap = locals().get('cap', None)
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
            cap_count = locals().get('cap_count', None)
            if cap_count is not None:
                try:
                    cap_count.release()
                except Exception:
                    pass
            err = f"Error: {e}\n\n{traceback.format_exc()}"
            self.error.emit(err)

    def cancel(self) -> None:
        self._cancel = True


# -------------------------
# Main Window
# -------------------------
class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Frame2Image")
        self.setMinimumSize(720, 420)

        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[FrameExtractorWorker] = None
        self._last_out_dir: Optional[str] = None
        self._started_at: Optional[float] = None
        self._total_for_run: Optional[int] = None
        self._has_cuda: Optional[bool] = None

        # Enable drag and drop for quick video selection
        self.setAcceptDrops(True)

        self._build_ui()
        self._wire_events()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)

        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Header title
        header = QtWidgets.QLabel("Frame2Image")
        header.setAlignment(QtCore.Qt.AlignHCenter)
        f = header.font()
        f.setPointSize(20)
        f.setBold(True)
        header.setFont(f)
        layout.addWidget(header)

        # Input group (no visible title)
        in_group = QtWidgets.QGroupBox()
        in_layout = QtWidgets.QGridLayout(in_group)
        in_layout.setVerticalSpacing(10)
        in_layout.setHorizontalSpacing(10)

        self.video_edit = QtWidgets.QLineEdit()
        self.video_edit.setPlaceholderText("Select a video file…")
        self.video_edit.setToolTip("Path to the input video file")
        self.video_btn = QtWidgets.QToolButton()
        self.video_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DialogOpenButton))
        self.video_btn.setIconSize(QtCore.QSize(24, 24))
        self.video_btn.setToolTip("Browse video file")

        self.out_edit = QtWidgets.QLineEdit()
        self.out_edit.setPlaceholderText("Choose output folder…")
        self.out_edit.setToolTip("Folder where frames will be saved")
        self.out_btn = QtWidgets.QToolButton()
        self.out_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        self.out_btn.setIconSize(QtCore.QSize(24, 24))
        self.out_btn.setToolTip("Choose output folder")

        # 2-column layout: field + icon button
        in_layout.addWidget(self.video_edit, 0, 0)
        in_layout.addWidget(self.video_btn, 0, 1)
        in_layout.addWidget(self.out_edit, 1, 0)
        in_layout.addWidget(self.out_btn, 1, 1)
        in_layout.setColumnStretch(0, 1)

        # Metadata label showing video info (resolution, duration, fps, frames)
        self.meta_label = QtWidgets.QLabel("")
        self.meta_label.setStyleSheet("color: #bbbbbb;")
        self.meta_label.setVisible(False)
        in_layout.addWidget(self.meta_label, 2, 0, 1, 2)

        # Time range controls
        times_row = QtWidgets.QWidget()
        times_layout = QtWidgets.QHBoxLayout(times_row)
        times_layout.setContentsMargins(0, 0, 0, 0)
        times_layout.setSpacing(8)
        times_layout.addWidget(QtWidgets.QLabel("Start"))
        self.start_time_edit = QtWidgets.QLineEdit()
        self.start_time_edit.setPlaceholderText("HH:MM:SS(.ms) or seconds")
        self.start_time_edit.setToolTip("Optional start time for extraction")
        self.start_time_edit.setFixedWidth(160)
        times_layout.addWidget(self.start_time_edit)
        times_layout.addSpacing(10)
        times_layout.addWidget(QtWidgets.QLabel("End"))
        self.end_time_edit = QtWidgets.QLineEdit()
        self.end_time_edit.setPlaceholderText("HH:MM:SS(.ms) or seconds")
        self.end_time_edit.setToolTip("Optional end time for extraction")
        self.end_time_edit.setFixedWidth(160)
        times_layout.addWidget(self.end_time_edit)
        times_layout.addStretch(1)
        in_layout.addWidget(times_row, 3, 0, 1, 2)

        # Precision frame counting toggle
        self.precision_check = QtWidgets.QCheckBox("Precision frame count (slower)")
        self.precision_check.setToolTip("Use ffprobe -count_frames for exact frame count; may be slow on long videos.")
        in_layout.addWidget(self.precision_check, 4, 0, 1, 2)

        layout.addWidget(in_group)

        # Controls group (no visible title)
        ctl_group = QtWidgets.QGroupBox()
        ctl_layout = QtWidgets.QHBoxLayout(ctl_group)
        ctl_layout.setSpacing(10)

        self.start_btn = QtWidgets.QPushButton("Start")
        self.cancel_btn = QtWidgets.QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.open_out_btn = QtWidgets.QToolButton()
        self.open_out_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        self.open_out_btn.setIconSize(QtCore.QSize(22, 22))
        self.open_out_btn.setToolTip("Open output folder")
        self.open_out_btn.setEnabled(False)

        # GPU status badge
        self.gpu_badge = QtWidgets.QLabel("GPU: Detecting…")
        self.gpu_badge.setAlignment(QtCore.Qt.AlignCenter)
        self.gpu_badge.setStyleSheet("border-radius: 10px; padding: 4px 8px; background: #555; color: white; font-weight: bold;")

        ctl_layout.addWidget(self.start_btn)
        ctl_layout.addWidget(self.cancel_btn)
        ctl_layout.addStretch(1)
        ctl_layout.addWidget(self.gpu_badge)
        ctl_layout.addWidget(self.open_out_btn)

        layout.addWidget(ctl_group)

        # Progress group (no visible title)
        prog_group = QtWidgets.QGroupBox()
        prog_layout = QtWidgets.QVBoxLayout(prog_group)
        prog_layout.setSpacing(8)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("")

        self.status = QtWidgets.QLabel("Idle.")
        self.status.setWordWrap(True)
        self.status.setVisible(False)

        prog_layout.addWidget(self.progress)
        prog_layout.addWidget(self.status)

        layout.addWidget(prog_group)

        layout.addStretch(1)

        # Detect GPU capability once and set badge
        try:
            ff = _ffmpeg_path_global()
            has_cuda = bool(ff and ffmpeg_supports_cuda(ff))
        except Exception:
            has_cuda = False
        self._has_cuda = has_cuda
        if has_cuda:
            self.gpu_badge.setText("GPU: NVDEC")
            self.gpu_badge.setStyleSheet("border-radius: 10px; padding: 4px 8px; background: #2e7d32; color: white; font-weight: bold;")
        else:
            self.gpu_badge.setText("GPU: CPU")
            self.gpu_badge.setStyleSheet("border-radius: 10px; padding: 4px 8px; background: #555; color: white; font-weight: bold;")

    def _wire_events(self) -> None:
        self.video_btn.clicked.connect(self.on_pick_video)
        self.out_btn.clicked.connect(self.on_pick_out)
        self.start_btn.clicked.connect(self.on_start)
        self.cancel_btn.clicked.connect(self.on_cancel)
        self.open_out_btn.clicked.connect(self.on_open_out)

    # ------------- UI actions -------------
    def update_metadata_for_path(self, path: str) -> None:
        if not path:
            return
        self.video_edit.setText(path)
        # prefill output to video's directory if empty
        if not self.out_edit.text():
            self.out_edit.setText(str(Path(path).parent))
        # Rich metadata via ffprobe
        meta = probe_video_metadata_with_ffprobe(path)
        self._current_meta = meta  # store for validation/use
        frames = int(meta.get("frames") or 0)
        frames_exact = bool(meta.get("frames_exact"))
        fps = meta.get("fps")
        dur = meta.get("duration")
        w = meta.get("width")
        h = meta.get("height")
        codec = meta.get("codec")
        parts = []
        if w and h:
            parts.append(f"{w}x{h}")
        if fps:
            parts.append(f"{fps:.3f} fps")
        if dur is not None:
            parts.append(f"{format_seconds(dur)}")
        if frames > 0:
            suffix = "" if frames_exact else " (approx.)"
            parts.append(f"{frames:,} frames{suffix}")
        if codec:
            parts.append(f"{codec}")
        text = "  •  ".join(parts) if parts else "Video metadata unavailable"
        self.meta_label.setText(text)
        self.meta_label.setVisible(True)

    def on_pick_video(self) -> None:
        filters = (
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.m4v *.mpg *.mpeg *.wmv);;"
            "All Files (*.*)"
        )
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Select video", str(Path.home()), filters)
        if path:
            self.update_metadata_for_path(path)

    def on_pick_out(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose output folder", str(Path.home()))
        if path:
            self.out_edit.setText(path)

    def on_start(self) -> None:
        video = self.video_edit.text().strip()
        out = self.out_edit.text().strip()

        if not video:
            QtWidgets.QMessageBox.warning(self, "Missing video", "Please select a video file.")
            return
        if not Path(video).exists():
            QtWidgets.QMessageBox.critical(self, "Invalid video", "The selected video file does not exist.")
            return
        if not out:
            QtWidgets.QMessageBox.warning(self, "Missing output", "Please choose an output folder.")
            return
        if not Path(out).exists():
            try:
                Path(out).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Output error", f"Could not create output folder:\n{e}")
                return

        # Parse time range
        start_s = parse_time_to_seconds(self.start_time_edit.text()) if hasattr(self, 'start_time_edit') else None
        end_s = parse_time_to_seconds(self.end_time_edit.text()) if hasattr(self, 'end_time_edit') else None
        if start_s is not None and start_s < 0:
            start_s = 0.0
        if end_s is not None and start_s is not None and end_s <= start_s:
            QtWidgets.QMessageBox.warning(self, "Invalid range", "End time must be greater than start time.")
            return
        # If we know duration, clamp range
        meta = getattr(self, '_current_meta', None)
        dur = (meta or {}).get('duration') if isinstance(meta, dict) else None
        if dur is not None:
            if start_s is not None and start_s >= dur:
                QtWidgets.QMessageBox.warning(self, "Invalid start", "Start time is beyond video duration.")
                return
            if end_s is not None and end_s > dur:
                end_s = dur

        precision = self.precision_check.isChecked() if hasattr(self, 'precision_check') else False

        # Prepare UI
        self._set_busy(True)
        self.status.setText("Preparing…")
        self.status.setVisible(True)
        self.progress.setRange(0, 0)  # busy until we know total
        self.progress.setValue(0)
        self.progress.setFormat("Extracting…")
        self.open_out_btn.setEnabled(False)
        self._started_at = time.time()
        self._total_for_run = None

        # Start worker thread
        self._thread = QtCore.QThread(self)
        self._worker = FrameExtractorWorker(video, out, start_time=start_s, end_time=end_s, precision_count=precision)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_progress)
        self._worker.message.connect(self.status.setText)
        self._worker.finished.connect(self.on_finished)
        self._worker.error.connect(self.on_error)

        # Ensure cleanup
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        # Also cleanup on error
        self._worker.error.connect(self._thread.quit)
        self._worker.error.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def on_cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            self.status.setText("Canceling…")
            self.cancel_btn.setEnabled(False)

    # ... (rest of the code remains the same)

    @QtCore.Slot(int, int)
    def on_progress(self, current: int, total: int) -> None:
        now = time.time()
        elapsed = (now - self._started_at) if self._started_at else 0.0
        fps = (current / elapsed) if elapsed > 0 else 0.0
        if total <= 0:
            # Unknown total: indeterminate bar
            self.progress.setRange(0, 0)
            self.progress.setFormat(f"{current} frames — {fps:.1f} fps")
        else:
            if self.progress.maximum() != total:
                self.progress.setRange(0, total)
            self.progress.setValue(current)
            eta_s = (total - current) / fps if fps > 0 else 0
            self.progress.setFormat(f"{current} / {total} frames — {fps:.1f} fps — ETA {format_seconds(eta_s)}")

    @QtCore.Slot(bool, bool, str, int)
    def on_finished(self, success: bool, canceled: bool, out_dir: str, frames_saved: int) -> None:
        self._last_out_dir = out_dir
        self._set_busy(False)
        self.cancel_btn.setEnabled(False)
        self.open_out_btn.setEnabled(True)
        # Hide status after finishing to keep UI minimal
        if success and not canceled:
            self.status.setVisible(False)
        elif canceled:
            # Briefly show canceled message, then hide; for simplicity, just hide immediately
            self.status.setVisible(False)
        else:
            # Keep visible on issues
            self.status.setText("Finished with issues.")
            self.status.setVisible(True)
        # Drop references so we don't touch deleted Qt objects later
        self._worker = None
        self._thread = None

    @QtCore.Slot(str)
    def on_error(self, err_text: str) -> None:
        self._set_busy(False)
        self.cancel_btn.setEnabled(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.status.setText("Error occurred.")
        self.status.setVisible(True)
        self.show_error_dialog("Error", err_text)

    # Custom error dialog with copy functionality
    def show_error_dialog(self, title: str, text: str) -> None:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(640, 360)
        v = QtWidgets.QVBoxLayout(dlg)
        lab = QtWidgets.QLabel("A detailed error log is shown below. You can copy it for support.")
        v.addWidget(lab)
        txt = QtWidgets.QPlainTextEdit()
        txt.setReadOnly(True)
        txt.setPlainText(text)
        v.addWidget(txt, 1)
        btns = QtWidgets.QHBoxLayout()
        btns.addStretch(1)
        copy_btn = QtWidgets.QPushButton("Copy")
        close_btn = QtWidgets.QPushButton("Close")
        btns.addWidget(copy_btn)
        btns.addWidget(close_btn)
        v.addLayout(btns)
        def copy():
            QtWidgets.QApplication.clipboard().setText(text)
        copy_btn.clicked.connect(copy)
        close_btn.clicked.connect(dlg.accept)
        dlg.exec()

    # Drag-and-drop support
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:  # type: ignore[override]
        mime = event.mimeData()
        if mime.hasUrls():
            # Accept if any url is a local file with video-like extension
            for url in mime.urls():
                if url.isLocalFile():
                    p = url.toLocalFile()
                    ext = Path(p).suffix.lower()
                    if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg", ".wmv"}:
                        event.acceptProposedAction()
                        return
        event.ignore()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:  # type: ignore[override]
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    p = url.toLocalFile()
                    ext = Path(p).suffix.lower()
                    if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg", ".wmv"}:
                        self.update_metadata_for_path(p)
                        event.acceptProposedAction()
                        return
        event.ignore()

    def _set_busy(self, busy: bool) -> None:
        self.video_btn.setEnabled(not busy)
        self.out_btn.setEnabled(not busy)
        self.start_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)

    # Ensure graceful stop on close
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        # Best-effort shutdown: don't call methods on possibly-deleted QThread
        w = self._worker
        th = self._thread
        if w is not None:
            try:
                w.cancel()
            except Exception:
                pass
        if th is not None:
            try:
                th.quit()
                th.wait(1500)
            except RuntimeError:
                # Underlying C++ object may already be deleted
                pass
            except Exception:
                pass
        # Clear refs to avoid later access to deleted Qt objects
        self._worker = None
        self._thread = None
        event.accept()


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    apply_dark_theme(app)

    w = MainWindow()
    w.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
