import os
import sys
import traceback
from pathlib import Path
from typing import Optional
import shutil
import subprocess
import json
import time
import math
import logging

import cv2
from PySide6 import QtCore, QtGui, QtWidgets
__version__ = "0.1.2"
# Lightweight logging setup
logger = logging.getLogger("frame2image")
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

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
    dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(60, 63, 65))
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
        QToolTip { color: #ffffff; background-color: #353535; border: 1px solid #4a4a4a; }
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

    def __init__(self, video_path: str, output_folder: str, start_time: Optional[float] = None, end_time: Optional[float] = None, precision_count: bool = False,
                 out_format: str = "png", jpeg_quality: int = 90, sample_every_n: int = 1, sample_every_t: float = 0.0):
        super().__init__()
        self.video_path = Path(video_path)
        self.output_folder = Path(output_folder)
        self._cancel = False
        self.start_time = start_time
        self.end_time = end_time
        self.precision_count = precision_count
        # Output options
        of = (out_format or "png").strip().lower()
        if of in {"jpg", "jpeg"}:
            of = "jpeg"
        elif of != "png":
            of = "png"
        self.out_format = of  # "png" or "jpeg"
        self.jpeg_quality = int(max(1, min(100, jpeg_quality)))
        # Sampling options
        self.sample_every_n = int(max(1, sample_every_n))
        self.sample_every_t = float(max(0.0, sample_every_t))
        logger.debug(
            "Worker init: video=%s, out=%s, range=(%s,%s), precision=%s, format=%s, jpeg_q=%s, every_n=%s, every_t=%s",
            self.video_path,
            self.output_folder,
            self.start_time,
            self.end_time,
            self.precision_count,
            self.out_format,
            self.jpeg_quality,
            self.sample_every_n,
            self.sample_every_t,
        )

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
        """Run FFmpeg with NVDEC (CUDA) to dump frames respecting output format and sampling. Returns frames_saved.
        Emits progress and respects cancellation.
        """
        # Ensure output dir exists
        out_dir.mkdir(parents=True, exist_ok=True)
        # Pattern and quality/filters
        ext = "jpg" if self.out_format == "jpeg" else "png"
        pattern = str(out_dir / f"frame_%0{pad}d.{ext}")
        # Build seek args
        seek_args = []
        dur_args = []
        if start_s is not None and start_s > 0:
            seek_args += ["-ss", f"{start_s:.3f}"]
        if end_s is not None and (start_s is not None) and (end_s > start_s):
            dur = max(0.0, end_s - start_s)
            dur_args += ["-t", f"{dur:.3f}"]
        # Build sampling filter
        vf_filters: list[str] = []
        if self.sample_every_t and self.sample_every_t > 0:
            try:
                rate = 1.0 / float(self.sample_every_t)
                if rate > 0:
                    vf_filters.append(f"fps=fps={rate:.6f}")
            except Exception:
                pass
        elif self.sample_every_n and self.sample_every_n > 1:
            # select every Nth decoded frame
            vf_filters.append(f"select=not(mod(n\\,{self.sample_every_n}))")
        vsync_args = ["-vsync", "vfr"] if vf_filters else ["-vsync", "0"]
        # Quality/format args
        quality_args: list[str] = []
        if self.out_format == "jpeg":
            # Map 1..100 -> qscale 31..2 (lower is better)
            qscale = int(round(31 - (self.jpeg_quality / 100.0) * 29))
            qscale = max(2, min(31, qscale))
            quality_args += ["-q:v", str(qscale)]
        else:
            quality_args += ["-compression_level", "3"]
        cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-y",
            "-hwaccel", "cuda",
            *seek_args,
            "-i", str(self.video_path),
            *dur_args,
            *( ["-vf", ",".join(vf_filters)] if vf_filters else [] ),
            *vsync_args,
            "-start_number", "1",
            *quality_args,
            pattern,
            "-progress", "pipe:1",
            "-nostats",
            "-loglevel", "error",
        ]

        self.message.emit("Using FFmpeg (NVDEC) for GPU-accelerated decoding…")
        logger.info("FFmpeg NVDEC path engaged: %s", ffmpeg_path)
        logger.debug("FFmpeg command: %s", " ".join(cmd))
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
                    saved = sum(1 for _ in out_dir.glob(f"frame_*.{ext}"))
                except Exception:
                    pass
                logger.info("FFmpeg NVDEC canceled by user; saved=%d", saved)
                return saved

            if proc.returncode != 0:
                err = ""
                try:
                    if proc.stderr is not None:
                        err = proc.stderr.read()
                except Exception:
                    pass
                logger.error("FFmpeg NVDEC failed with code %s", proc.returncode)
                raise RuntimeError(f"FFmpeg failed (exit {proc.returncode}).\n{err}")

            if saved == 0:
                # Fallback to counting files if 'frame=' wasn't seen
                try:
                    saved = sum(1 for _ in out_dir.glob(f"frame_*.{ext}"))
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
            logger.info("Worker run start: %s", self.video_path)
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

            # Adjust expected total for sampling
            frames_planned = frames_in_range
            if self.sample_every_t and self.sample_every_t > 0:
                # Estimate by duration window / T
                window_dur = None
                try:
                    if end_s is not None:
                        window_dur = max(0.0, end_s - start_s)
                    else:
                        d = meta.get("duration")
                        if d is not None:
                            window_dur = max(0.0, float(d) - start_s)
                except Exception:
                    window_dur = None
                if window_dur is not None and window_dur > 0:
                    try:
                        frames_planned = max(1, int(math.floor(window_dur / self.sample_every_t)) + 1)
                    except Exception:
                        frames_planned = 0
                else:
                    # Unknown
                    frames_planned = 0
            elif self.sample_every_n and self.sample_every_n > 1 and frames_in_range and frames_in_range > 0:
                try:
                    frames_planned = int(math.ceil(frames_in_range / self.sample_every_n))
                except Exception:
                    frames_planned = frames_in_range

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
            pad = len(str(frames_planned)) if frames_planned and frames_planned > 0 else 6

            # Prefer FFmpeg with NVDEC (CUDA) if available; fall back to OpenCV
            ffmpeg_path = self._ffmpeg_path()
            if ffmpeg_path and self._ffmpeg_supports_cuda(ffmpeg_path):
                try:
                    saved = self._run_ffmpeg_nvdec(ffmpeg_path, out_dir, pad, frames_planned or 0, start_s if self.start_time else 0.0, end_s)
                    if self._cancel:
                        self.message.emit("Canceled by user.")
                        self.finished.emit(False, True, str(out_dir), saved)
                    else:
                        if frames_planned and frames_planned > 0:
                            self.progress.emit(min(saved, frames_planned), frames_planned)
                        self.message.emit("Done.")
                        self.finished.emit(True, False, str(out_dir), saved)
                    logger.info("Worker completed via FFmpeg NVDEC: canceled=%s saved=%d", self._cancel, saved)
                    return
                except Exception as e_ff:
                    # Inform user and continue with CPU fallback
                    self.message.emit(f"FFmpeg GPU path failed, falling back to CPU (OpenCV)…\n{e_ff}")
                    logger.warning("FFmpeg NVDEC path failed; falling back to OpenCV: %s", e_ff)

            # ---------- OpenCV CPU fallback ----------
            logger.info("Starting OpenCV CPU fallback for extraction")
            cap = cv2.VideoCapture(str(self.video_path))
            if not cap.isOpened():
                raise RuntimeError("Failed to open video. Try installing codecs/FFmpeg or a different file.")

            # Seek to start time if specified
            if self.start_time and self.start_time > 0:
                try:
                    cap.set(cv2.CAP_PROP_POS_MSEC, self.start_time * 1000.0)
                except Exception:
                    pass

            # Choose output format params
            if self.out_format == "jpeg":
                img_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
                out_ext = "jpg"
            else:
                img_params = [cv2.IMWRITE_PNG_COMPRESSION, 3]  # lossless; 0-9 only changes size/speed
                out_ext = "png"

            self.message.emit("Starting extraction…")
            if frames_in_range and frames_in_range > 0:
                self.progress.emit(0, frames_in_range)
            else:
                self.progress.emit(0, 0)

            saved = 0
            throttle = 10  # emit progress every N frames to reduce signal overhead
            frame_index = 0  # count of frames read
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
            # For time-based sampling, track next timestamp to save
            next_ms = None
            if self.sample_every_t and self.sample_every_t > 0:
                try:
                    next_ms = (self.start_time or 0.0) * 1000.0
                except Exception:
                    next_ms = None

            while not self._cancel:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_index += 1

                # Stop at end time if defined
                if end_limit_frames is not None and frame_index >= end_limit_frames:
                    break
                if end_limit_ms is not None:
                    try:
                        pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                        if pos_ms and pos_ms > end_limit_ms:
                            break
                    except Exception:
                        pass

                # Decide whether to save this frame based on sampling settings
                do_save = False
                if self.sample_every_t and self.sample_every_t > 0:
                    pos_ms = None
                    try:
                        pos_ms = cap.get(cv2.CAP_PROP_POS_MSEC)
                    except Exception:
                        pos_ms = None
                    if (pos_ms is None) and fps_eff:
                        try:
                            pos_ms = (frame_index - 1) * (1000.0 / float(fps_eff))
                        except Exception:
                            pos_ms = None
                    if next_ms is None and pos_ms is not None:
                        next_ms = pos_ms
                    if pos_ms is not None and next_ms is not None and (pos_ms + 1e-3) >= next_ms:
                        do_save = True
                        next_ms = next_ms + (self.sample_every_t * 1000.0)
                elif self.sample_every_n and self.sample_every_n > 1:
                    do_save = ((frame_index - 1) % self.sample_every_n == 0)
                else:
                    do_save = True

                if do_save:
                    filename = out_dir / f"frame_{saved + 1:0{pad}d}.{out_ext}"
                    ok = cv2.imwrite(str(filename), frame, img_params)
                    if not ok:
                        raise RuntimeError(f"Failed to write frame to {filename}")
                    saved += 1

                if frames_planned and frames_planned > 0:
                    if saved % throttle == 0 or saved == frames_planned:
                        self.progress.emit(saved, frames_planned)
                else:
                    if saved % throttle == 0:
                        self.progress.emit(saved, 0)

            cap.release()

            if self._cancel:
                self.message.emit("Canceled by user.")
                self.finished.emit(False, True, str(out_dir), saved)
                logger.info("Worker canceled during OpenCV path; saved=%d", saved)
            else:
                # Final progress update
                if frames_planned and frames_planned > 0:
                    self.progress.emit(min(saved, frames_planned), frames_planned)
                self.message.emit("Done.")
                self.finished.emit(True, False, str(out_dir), saved)
                logger.info("Worker finished (OpenCV path); saved=%d", saved)
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
            logger.exception("Worker error: %s", e)

    def cancel(self) -> None:
        self._cancel = True
        logger.info("Worker cancel requested")


# -------------------------
# Main Window
# -------------------------
class MainWindow(QtWidgets.QMainWindow):
    # Queued signal to request preview decoding at a specific millisecond timestamp
    preview_request_ms = QtCore.Signal(float)

    class _PreviewWorker(QtCore.QObject):
        frame_ready = QtCore.Signal(QtGui.QImage, float)
        error = QtCore.Signal(str)

        def __init__(self, video_path: str):
            super().__init__()
            self.video_path = str(video_path)
            self._cap: Optional[cv2.VideoCapture] = None
            self._pending_ms: Optional[float] = None
            self._working: bool = False

        @QtCore.Slot()
        def close(self) -> None:
            cap = self._cap
            self._cap = None
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass

        @QtCore.Slot(float)
        def request_ms(self, ms: float) -> None:
            # Coalesce requests: always keep latest request and process sequentially
            self._pending_ms = float(ms)
            if not self._working:
                self._process()

        def _ensure_cap(self) -> bool:
            if self._cap is None:
                c = cv2.VideoCapture(self.video_path)
                if not c.isOpened():
                    self.error.emit("Preview unavailable (failed to open video)")
                    return False
                self._cap = c
            return True

        def _process(self) -> None:
            if self._working:
                return
            self._working = True
            try:
                while self._pending_ms is not None:
                    ms = float(self._pending_ms)
                    self._pending_ms = None
                    if not self._ensure_cap():
                        break
                    try:
                        self._cap.set(cv2.CAP_PROP_POS_MSEC, ms)
                    except Exception:
                        pass
                    ok, frame = self._cap.read()
                    if not ok or frame is None:
                        # Some codecs need an extra read after seek
                        ok, frame = self._cap.read()
                    if not ok or frame is None:
                        self.error.emit("Preview unavailable")
                        continue
                    try:
                        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        h, w, ch = rgb.shape
                        bytes_per_line = ch * w
                        qimg = QtGui.QImage(rgb.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888).copy()
                        self.frame_ready.emit(qimg, ms)
                    except Exception as e:
                        self.error.emit(f"Preview conversion failed: {e}")
                        continue
            finally:
                self._working = False

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Frame2Image v{__version__}")
        self.setMinimumSize(720, 420)

        self._thread: Optional[QtCore.QThread] = None
        self._worker: Optional[FrameExtractorWorker] = None
        self._last_out_dir: Optional[str] = None
        self._started_at: Optional[float] = None
        self._total_for_run: Optional[int] = None
        self._has_cuda: Optional[bool] = None
        self._settings: QtCore.QSettings = QtCore.QSettings("ElfyDelphi", "Frame2Image")

        # Preview state
        self._preview_cap: Optional[cv2.VideoCapture] = None
        self._preview_duration_ms: Optional[float] = None
        self._preview_window_start_ms: float = 0.0
        self._preview_window_end_ms: Optional[float] = None
        self._last_preview_qimg: Optional[QtGui.QImage] = None
        # Async preview decoding
        self._preview_thread: Optional[QtCore.QThread] = None
        self._preview_worker: Optional['MainWindow._PreviewWorker'] = None

        # Enable drag and drop for quick video selection
        self.setAcceptDrops(True)

        self._build_ui()
        self._wire_events()
        self._load_settings()

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
        self.open_in_btn = QtWidgets.QToolButton()
        self.open_in_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon))
        self.open_in_btn.setIconSize(QtCore.QSize(22, 22))
        self.open_in_btn.setToolTip("Open input folder")
        self.open_in_btn.setEnabled(False)

        self.out_edit = QtWidgets.QLineEdit()
        self.out_edit.setPlaceholderText("Choose output folder…")
        self.out_edit.setToolTip("Folder where frames will be saved")
        self.out_btn = QtWidgets.QToolButton()
        self.out_btn.setIcon(self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        self.out_btn.setIconSize(QtCore.QSize(24, 24))
        self.out_btn.setToolTip("Choose output folder")

        # 3-column layout: field + browse + open-in
        in_layout.addWidget(self.video_edit, 0, 0)
        in_layout.addWidget(self.video_btn, 0, 1)
        in_layout.addWidget(self.open_in_btn, 0, 2)
        in_layout.addWidget(self.out_edit, 1, 0)
        in_layout.addWidget(self.out_btn, 1, 1)
        in_layout.setColumnStretch(0, 1)

        # Metadata label showing video info (resolution, duration, fps, frames)
        self.meta_label = QtWidgets.QLabel("")
        self.meta_label.setStyleSheet("color: #bbbbbb;")
        self.meta_label.setVisible(False)
        in_layout.addWidget(self.meta_label, 2, 0, 1, 3)

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
        in_layout.addWidget(times_row, 3, 0, 1, 3)

        # Precision frame counting toggle
        self.precision_check = QtWidgets.QCheckBox("Precision frame count (slower)")
        self.precision_check.setToolTip("Use ffprobe -count_frames for exact frame count; may be slow on long videos.")
        in_layout.addWidget(self.precision_check, 4, 0, 1, 3)

        layout.addWidget(in_group)

        # Preview group
        preview_group = QtWidgets.QGroupBox("Preview")
        preview_layout = QtWidgets.QVBoxLayout(preview_group)
        preview_layout.setSpacing(8)
        self.preview_label = QtWidgets.QLabel("No video selected")
        self.preview_label.setAlignment(QtCore.Qt.AlignCenter)
        self.preview_label.setMinimumHeight(220)
        self.preview_label.setStyleSheet("background: #111; border: 1px solid #333; border-radius: 6px;")
        self.preview_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.preview_label.setVisible(True)
        # Re-scale the last preview image when the label resizes
        self.preview_label.installEventFilter(self)
        preview_layout.addWidget(self.preview_label, 1)

        preview_controls = QtWidgets.QHBoxLayout()
        preview_controls.setSpacing(8)
        self.preview_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.preview_slider.setRange(0, 1000)
        self.preview_slider.setEnabled(False)
        self.preview_time_label = QtWidgets.QLabel("--:-- / --:--")
        self.preview_time_label.setStyleSheet("color: #bbbbbb;")
        preview_controls.addWidget(self.preview_slider, 1)
        preview_controls.addWidget(self.preview_time_label)
        preview_layout.addLayout(preview_controls)

        layout.addWidget(preview_group)

        # Output options and sampling group (no visible title)
        opts_group = QtWidgets.QGroupBox()
        opts_layout = QtWidgets.QGridLayout(opts_group)
        opts_layout.setVerticalSpacing(10)
        opts_layout.setHorizontalSpacing(10)

        # Output format
        opts_layout.addWidget(QtWidgets.QLabel("Output format"), 0, 0)
        self.format_combo = QtWidgets.QComboBox()
        self.format_combo.addItem("PNG (lossless)", userData="png")
        self.format_combo.addItem("JPEG (lossy)", userData="jpeg")
        self.format_combo.setToolTip("Choose image format for extracted frames")
        opts_layout.addWidget(self.format_combo, 0, 1)

        # JPEG quality
        self.quality_label = QtWidgets.QLabel("Quality: 90")
        self.quality_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setValue(90)
        self.quality_slider.setToolTip("JPEG quality (higher = better quality and size)")
        opts_layout.addWidget(self.quality_label, 1, 0)
        opts_layout.addWidget(self.quality_slider, 1, 1)

        # Sampling controls
        opts_layout.addWidget(QtWidgets.QLabel("Sample every Nth frame"), 2, 0)
        self.sample_n_spin = QtWidgets.QSpinBox()
        self.sample_n_spin.setRange(1, 1000000)
        self.sample_n_spin.setValue(1)
        self.sample_n_spin.setToolTip("Save one out of every N frames (1 = all frames)")
        opts_layout.addWidget(self.sample_n_spin, 2, 1)

        opts_layout.addWidget(QtWidgets.QLabel("Or every T seconds"), 3, 0)
        self.sample_t_spin = QtWidgets.QDoubleSpinBox()
        self.sample_t_spin.setRange(0.0, 1e6)
        self.sample_t_spin.setDecimals(3)
        self.sample_t_spin.setSingleStep(0.1)
        self.sample_t_spin.setValue(0.0)
        self.sample_t_spin.setSuffix(" s")
        self.sample_t_spin.setToolTip("Time-based sampling; if > 0, overrides Nth frame option")
        opts_layout.addWidget(self.sample_t_spin, 3, 1)

        layout.addWidget(opts_group)

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
        self.auto_open_check = QtWidgets.QCheckBox("Open folder when done")
        self.auto_open_check.setToolTip("Automatically open the output folder after a successful extraction")
        self.auto_open_check.setChecked(False)

        # GPU status badge
        self.gpu_badge = QtWidgets.QLabel("GPU: Detecting…")
        self.gpu_badge.setAlignment(QtCore.Qt.AlignCenter)
        self.gpu_badge.setStyleSheet("border-radius: 10px; padding: 4px 8px; background: #555; color: white; font-weight: bold;")

        ctl_layout.addWidget(self.start_btn)
        ctl_layout.addWidget(self.cancel_btn)
        ctl_layout.addStretch(1)
        ctl_layout.addWidget(self.gpu_badge)
        ctl_layout.addWidget(self.auto_open_check)
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
        self.open_in_btn.clicked.connect(self.on_open_in)
        self.video_edit.textChanged.connect(self._on_video_text_changed)
        # Preview interactions
        self.preview_slider.valueChanged.connect(self._on_preview_slider_changed)
        # Update preview window when time range changes
        self.start_time_edit.editingFinished.connect(self._on_time_range_changed)
        self.end_time_edit.editingFinished.connect(self._on_time_range_changed)
        # Format/quality
        def on_fmt_change():
            fmt = (self.format_combo.currentData() or "png").lower()
            is_jpeg = fmt == "jpeg"
            self.quality_slider.setEnabled(is_jpeg)
            self.quality_label.setEnabled(is_jpeg)
        self.format_combo.currentIndexChanged.connect(on_fmt_change)
        self.quality_slider.valueChanged.connect(lambda v: self.quality_label.setText(f"Quality: {v}"))
        # Initialize enabled state
        QtCore.QTimer.singleShot(0, on_fmt_change)

    # -------- Settings helpers --------
    def _load_settings(self) -> None:
        try:
            last_out = self._settings.value("last_output_dir", "", type=str) or ""
            if last_out:
                self.out_edit.setText(last_out)
            last_vid = self._settings.value("last_video_path", "", type=str) or ""
            if last_vid and Path(last_vid).exists():
                # Set without overriding out_edit if already set
                self.video_edit.setText(last_vid)
                self.update_metadata_for_path(last_vid)
            st = self._settings.value("start_time", "", type=str) or ""
            et = self._settings.value("end_time", "", type=str) or ""
            if st:
                self.start_time_edit.setText(st)
            if et:
                self.end_time_edit.setText(et)
            prec = self._settings.value("precision", False)
            if isinstance(prec, str):
                prec = prec.lower() in {"1", "true", "yes", "on"}
            self.precision_check.setChecked(bool(prec))
            ao = self._settings.value("auto_open", False)
            if isinstance(ao, str):
                ao = ao.lower() in {"1", "true", "yes", "on"}
            self.auto_open_check.setChecked(bool(ao))
            # Output format and quality
            fmt = self._settings.value("out_format", "png", type=str) or "png"
            idx = max(0, self.format_combo.findData(fmt))
            self.format_combo.setCurrentIndex(idx)
            q = self._settings.value("jpeg_quality", 90)
            try:
                q = int(q)
            except Exception:
                q = 90
            q = max(1, min(100, q))
            self.quality_slider.setValue(q)
            # Sampling
            n = self._settings.value("sample_every_n", 1)
            try:
                n = int(n)
            except Exception:
                n = 1
            self.sample_n_spin.setValue(max(1, n))
            t = self._settings.value("sample_every_t", 0.0)
            try:
                t = float(t)
            except Exception:
                t = 0.0
            self.sample_t_spin.setValue(max(0.0, t))
            # Restore window geometry (size/position)
            geom = self._settings.value("window_geometry", None, type=QtCore.QByteArray)
            if geom:
                try:
                    self.restoreGeometry(geom)
                except Exception:
                    pass
        except Exception:
            pass

    def _save_settings(self) -> None:
        try:
            self._settings.setValue("last_output_dir", self.out_edit.text().strip())
            self._settings.setValue("last_video_path", self.video_edit.text().strip())
            self._settings.setValue("start_time", self.start_time_edit.text().strip())
            self._settings.setValue("end_time", self.end_time_edit.text().strip())
            self._settings.setValue("precision", self.precision_check.isChecked())
            self._settings.setValue("auto_open", self.auto_open_check.isChecked())
            # New options
            self._settings.setValue("out_format", (self.format_combo.currentData() or "png"))
            self._settings.setValue("jpeg_quality", int(self.quality_slider.value()))
            self._settings.setValue("sample_every_n", int(self.sample_n_spin.value()))
            self._settings.setValue("sample_every_t", float(self.sample_t_spin.value()))
            # Save window geometry (size/position)
            self._settings.setValue("window_geometry", self.saveGeometry())
        except Exception:
            pass

    # ------------- UI actions -------------
    def update_metadata_for_path(self, path: str) -> None:
        if not path:
            return
        self.video_edit.setText(path)
        # prefill output to video's directory if empty
        if not self.out_edit.text():
            self.out_edit.setText(str(Path(path).parent))
        try:
            self._settings.setValue("last_video_path", path)
        except Exception:
            pass
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
        logger.info(
            "Loaded metadata for %s: frames=%s exact=%s fps=%s dur=%s size=%sx%s codec=%s",
            path,
            frames,
            frames_exact,
            fps,
            dur,
            w,
            h,
            codec,
        )
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

        # Initialize preview for this video
        self._init_preview_for_current_video()

    # ------- Preview helpers (class methods) -------
    def _close_preview_cap(self) -> None:
        cap = self._preview_cap
        self._preview_cap = None
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
        # Also stop preview worker thread if running
        th = getattr(self, "_preview_thread", None)
        worker = getattr(self, "_preview_worker", None)
        self._preview_worker = None
        if worker is not None:
            try:
                worker.close()
            except Exception:
                pass
        if th is not None:
            try:
                th.quit()
                th.wait(800)
            except Exception:
                pass
            self._preview_thread = None
        logger.debug("Preview resources closed")

    def _init_preview_for_current_video(self) -> None:
        path = self.video_edit.text().strip()
        self._close_preview_cap()
        self._last_preview_qimg = None
        self.preview_label.setText("Loading preview…" if path else "No video selected")
        self.preview_label.setPixmap(QtGui.QPixmap())
        self.preview_slider.setEnabled(False)
        self.preview_time_label.setText("--:-- / --:--")
        if not path or not Path(path).exists():
            logger.info("Preview init skipped: missing path")
            return
        tmp_cap = cv2.VideoCapture(path)
        if not tmp_cap.isOpened():
            self.preview_label.setText("Preview unavailable (failed to open video)")
            logger.warning("Preview failed to open video: %s", path)
            return
        # Determine duration (prefer metadata if available)
        dur_ms: Optional[float] = None
        try:
            meta = getattr(self, "_current_meta", None) or {}
            d = meta.get("duration") if isinstance(meta, dict) else None
            if d is not None:
                dur_ms = float(d) * 1000.0
        except Exception:
            dur_ms = None
        if not dur_ms or dur_ms <= 0:
            try:
                frame_count = tmp_cap.get(cv2.CAP_PROP_FRAME_COUNT)
                fps = tmp_cap.get(cv2.CAP_PROP_FPS)
                if frame_count and fps and fps > 0:
                    dur_ms = float(frame_count) / float(fps) * 1000.0
            except Exception:
                dur_ms = None
        try:
            tmp_cap.release()
        except Exception:
            pass
        self._preview_duration_ms = dur_ms if dur_ms and dur_ms > 0 else None
        # Start background preview worker
        try:
            th = QtCore.QThread(self)
            worker = MainWindow._PreviewWorker(path)
            worker.moveToThread(th)
            self.preview_request_ms.connect(worker.request_ms)
            worker.frame_ready.connect(self._on_preview_frame_ready)
            worker.error.connect(self._on_preview_error)
            th.finished.connect(worker.deleteLater)
            self._preview_thread = th
            self._preview_worker = worker
            th.start()
            logger.info("Preview worker started for %s (duration_ms=%s)", path, self._preview_duration_ms)
        except Exception:
            self._preview_thread = None
            self._preview_worker = None
            logger.exception("Failed to start preview worker for %s", path)
        # Update slider and show first frame
        self._refresh_preview_window_and_show(start_ratio=0.0)

    def _get_time_window_ms(self) -> tuple[float, Optional[float]]:
        total_ms = self._preview_duration_ms or 0.0
        st = parse_time_to_seconds(self.start_time_edit.text()) if hasattr(self, 'start_time_edit') else None
        et = parse_time_to_seconds(self.end_time_edit.text()) if hasattr(self, 'end_time_edit') else None
        st_ms = max(0.0, float(st) * 1000.0) if st is not None else 0.0
        end_ms = None
        if et is not None:
            end_ms = max(0.0, float(et) * 1000.0)
            if total_ms > 0:
                end_ms = min(end_ms, total_ms)
            if end_ms <= st_ms:
                # invalid range -> ignore end
                end_ms = None
        if (end_ms is None) and total_ms > 0:
            end_ms = total_ms
        # Clamp start to total
        if total_ms > 0 and st_ms >= total_ms:
            st_ms = max(0.0, total_ms - 1.0)
        return st_ms, end_ms

    def _refresh_preview_window_and_show(self, start_ratio: float = 0.0) -> None:
        # Compute window
        st_ms, end_ms = self._get_time_window_ms()
        self._preview_window_start_ms = st_ms
        self._preview_window_end_ms = end_ms
        have_cap = self._preview_cap is not None
        have_dur = (self._preview_duration_ms is not None) and (self._preview_duration_ms > 0)
        can_seek = have_cap and end_ms is not None and end_ms > st_ms and have_dur
        self.preview_slider.setEnabled(bool(can_seek))
        if can_seek:
            # Set slider to start and show frame
            v = int(max(0, min(1000, round(start_ratio * 1000.0))))
            # Block signals during programmatic update
            try:
                self.preview_slider.blockSignals(True)
                self.preview_slider.setValue(v)
            finally:
                self.preview_slider.blockSignals(False)
            self._show_preview_at_ratio(v / 1000.0)
        else:
            # Still try to show first frame
            self._show_preview_at_ms(st_ms)

    def _on_time_range_changed(self) -> None:
        # When time range edits change, recompute window and show start
        self._refresh_preview_window_and_show(start_ratio=0.0)

    def _on_preview_slider_changed(self, value: int) -> None:
        r = max(0.0, min(1.0, float(value) / 1000.0))
        self._show_preview_at_ratio(r)

    def _update_preview_time_label(self, cur_ms: Optional[float]) -> None:
        total_s = (self._preview_duration_ms or 0.0) / 1000.0
        cur_s = (cur_ms or 0.0) / 1000.0
        self.preview_time_label.setText(f"{format_seconds(cur_s)} / {format_seconds(total_s)}")

    def _show_preview_at_ratio(self, r: float) -> None:
        st_ms = self._preview_window_start_ms or 0.0
        end_ms = self._preview_window_end_ms
        if end_ms is None or end_ms <= st_ms:
            # Fallback to absolute 0..duration
            total = self._preview_duration_ms or 0.0
            target_ms = r * total
        else:
            target_ms = st_ms + r * max(0.0, (end_ms - st_ms))
        self._show_preview_at_ms(target_ms)

    def _show_preview_at_ms(self, ms: float) -> None:
        # Request async decoding in the background thread (queued connection)
        if self._preview_worker is not None:
            try:
                self.preview_request_ms.emit(float(ms))
            except Exception:
                # As a fallback, try direct call (may run in current thread)
                try:
                    self._preview_worker.request_ms(float(ms))
                except Exception:
                    pass
            return
        # Fallback UI message if worker is not available yet
        self.preview_label.setText("Loading preview…")

    def _apply_qimage_to_preview_label(self, qimg: QtGui.QImage) -> None:
        # Scale while keeping aspect ratio to fit label size
        target_size = self.preview_label.size()
        if target_size.width() < 2 or target_size.height() < 2:
            pix = QtGui.QPixmap.fromImage(qimg)
            self.preview_label.setPixmap(pix)
            return
        pix = QtGui.QPixmap.fromImage(qimg)
        scaled = pix.scaled(target_size, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)

    def _on_preview_frame_ready(self, qimg: QtGui.QImage, ms: float) -> None:
        self._last_preview_qimg = qimg
        self._apply_qimage_to_preview_label(qimg)
        self._update_preview_time_label(ms)

    def _on_preview_error(self, msg: str) -> None:
        # If we have an image already, keep showing it; otherwise show message
        if self._last_preview_qimg is None:
            self.preview_label.setText(msg or "Preview unavailable")
        logger.warning("Preview error: %s", msg)

    def on_pick_video(self) -> None:
        filters = (
            "Video Files (*.mp4 *.mov *.avi *.mkv *.webm *.m4v *.mpg *.mpeg *.wmv);;All Files (*)"
        )
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select video", str(Path.home()), filters
        )
        if path:
            self.update_metadata_for_path(path)

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        try:
            if obj is getattr(self, "preview_label", None) and event.type() == QtCore.QEvent.Resize:
                if self._last_preview_qimg is not None:
                    self._apply_qimage_to_preview_label(self._last_preview_qimg)
        except Exception:
            pass
        return QtWidgets.QMainWindow.eventFilter(self, obj, event)

    # Drag-and-drop support
    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:  # type: ignore[override]
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    p = url.toLocalFile()
                    path_obj = Path(p)
                    if path_obj.is_dir():
                        event.acceptProposedAction()
                        return
                    ext = path_obj.suffix.lower()
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
                    path_obj = Path(p)
                    if path_obj.is_dir():
                        # Treat as output folder
                        self.out_edit.setText(str(path_obj))
                        try:
                            self._settings.setValue("last_output_dir", str(path_obj))
                        except Exception:
                            pass
                        event.acceptProposedAction()
                        return
                    ext = path_obj.suffix.lower()
                    if ext in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".mpg", ".mpeg", ".wmv"}:
                        self.update_metadata_for_path(str(path_obj))
                        event.acceptProposedAction()
                        return
        event.ignore()

    def on_pick_out(self) -> None:
        path = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose output folder", str(Path.home()))
        if path:
            self.out_edit.setText(path)

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
            # Auto-open output folder if requested
            if self.auto_open_check.isChecked() and out_dir:
                self._open_dir(out_dir)
        elif canceled:
            # Briefly show canceled message, then hide; for simplicity, just hide immediately
            self.status.setVisible(False)
        else:
            # Keep visible on issues
            self.status.setText("Finished with issues.")
            self.status.setVisible(True)
        # Log completion summary
        try:
            elapsed = (time.time() - self._started_at) if self._started_at else None
        except Exception:
            elapsed = None
        logger.info(
            "Extraction finished: success=%s canceled=%s frames_saved=%s out_dir=%s elapsed=%s",
            success,
            canceled,
            frames_saved,
            out_dir,
            f"{elapsed:.2f}s" if isinstance(elapsed, (int, float)) else "n/a",
        )
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
        logger.error("Extraction error: %s", (err_text or "").splitlines()[0] if err_text else "unknown")
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

    # -------- Open output helpers --------
    def _open_dir(self, path: str) -> None:
        try:
            p = Path(path)
            if not p.exists():
                QtWidgets.QMessageBox.warning(self, "Missing folder", f"Folder does not exist:\n{path}")
                return
            url = QtCore.QUrl.fromLocalFile(str(p))
            if not QtGui.QDesktopServices.openUrl(url):
                # Fallback per-OS
                if sys.platform.startswith("win"):
                    os.startfile(str(p))  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(p)])
                else:
                    subprocess.Popen(["xdg-open", str(p)])
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Open folder failed", f"Could not open folder:\n{e}")

    def on_open_out(self) -> None:
        path = self._last_out_dir or self.out_edit.text().strip()
        if not path:
            QtWidgets.QMessageBox.information(self, "No folder", "No output folder available yet.")
            return
        self._open_dir(path)

    def on_open_in(self) -> None:
        path = self.video_edit.text().strip()
        if not path:
            QtWidgets.QMessageBox.information(self, "No input", "No input video selected yet.")
            return
        p = Path(path)
        parent = p.parent if p.parent != p else p
        if p.exists():
            # Open containing folder of the selected video
            self._open_dir(str(parent))
        else:
            # If file missing, try opening its parent folder if it exists
            if parent.exists():
                self._open_dir(str(parent))
            else:
                QtWidgets.QMessageBox.warning(self, "Missing folder", f"Input path does not exist:\n{path}")

    def _on_video_text_changed(self, _text: str) -> None:
        self.open_in_btn.setEnabled(bool(self.video_edit.text().strip()))

    # -------- Extraction controls --------
    def _set_busy(self, busy: bool) -> None:
        self.start_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(busy)
        self.video_btn.setEnabled(not busy)
        self.out_btn.setEnabled(not busy)
        self.video_edit.setEnabled(not busy)
        self.out_edit.setEnabled(not busy)
        self.preview_slider.setEnabled(not busy and self.preview_slider.isEnabled())

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
        # Clamp to duration if known
        meta = getattr(self, '_current_meta', None)
        dur = (meta or {}).get('duration') if isinstance(meta, dict) else None
        if dur is not None:
            if start_s is not None and start_s >= dur:
                QtWidgets.QMessageBox.warning(self, "Invalid start", "Start time is beyond video duration.")
                return
            if end_s is not None and end_s > dur:
                end_s = dur

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
        logger.info(
            "Start extraction: video=%s out=%s start=%s end=%s fmt=%s jpeg_q=%s every_n=%s every_t=%s precision=%s",
            video,
            out,
            start_s,
            end_s,
            (self.format_combo.currentData() or "png"),
            int(self.quality_slider.value()),
            int(self.sample_n_spin.value()),
            float(self.sample_t_spin.value()),
            self.precision_check.isChecked(),
        )

        # Persist current selections
        self._save_settings()

        # Start worker thread
        self._thread = QtCore.QThread(self)
        # Collect options
        out_format = (self.format_combo.currentData() or "png")
        jpeg_quality = int(self.quality_slider.value())
        sample_every_n = int(self.sample_n_spin.value())
        sample_every_t = float(self.sample_t_spin.value())

        self._worker = FrameExtractorWorker(
            video,
            out,
            start_time=start_s,
            end_time=end_s,
            precision_count=self.precision_check.isChecked(),
            out_format=out_format,
            jpeg_quality=jpeg_quality,
            sample_every_n=sample_every_n,
            sample_every_t=sample_every_t,
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.on_progress)
        self._worker.message.connect(self.status.setText)
        self._worker.finished.connect(self.on_finished)
        self._worker.error.connect(self.on_error)
        # Ensure cleanup
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.error.connect(self._thread.quit)
        self._worker.error.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def on_cancel(self) -> None:
        w = self._worker
        if w is not None:
            try:
                w.cancel()
            except Exception:
                pass
        self.status.setText("Canceling…")
        self.status.setVisible(True)
        logger.info("Cancel requested by user")

    # Ensure graceful stop on close
    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # type: ignore[override]
        # Save settings and stop preview worker/thread
        logger.info("Main window closing; starting cleanup")
        try:
            self._save_settings()
        except Exception:
            pass
        try:
            self._close_preview_cap()
        except Exception:
            pass
        # Stop extraction worker/thread robustly
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
                pass
            except Exception:
                pass
        self._worker = None
        self._thread = None
        event.accept()
        logger.info("Cleanup finished; app closed")


 
def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    apply_dark_theme(app)

    w = MainWindow()
    w.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
