"""Video Frame Extractor GUI application using customtkinter and FFmpeg."""

import os
import shutil
import subprocess
import sys
import threading
import time
import tkinter as tk  # For filedialog
from tkinter import filedialog, messagebox

import customtkinter

__version__ = "1.0.0"

# Embedded fallback MIT license text (used if LICENSE file cannot be read)
MIT_LICENSE_FALLBACK = (
    "MIT License\n\n"
    "Copyright (c) 2025 ElfyDelphi\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
    'of this software and associated documentation files (the "Software"), to deal\n'
    "in the Software without restriction, including without limitation the rights\n"
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
    "copies of the Software, and to permit persons to whom the Software is\n"
    "furnished to do so, subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all\n"
    "copies or substantial portions of the Software.\n\n"
    'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n'
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
    "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
    "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
    "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
    "SOFTWARE.\n"
)


class FrameExtractorApp:
    """Main application class for the Video Frame Extractor."""

    def __init__(self, root):
        """Initialize the application UI and components."""
        customtkinter.set_appearance_mode("dark")  # Modes: "System" (default), "Light", "Dark"
        customtkinter.set_default_color_theme("blue")  # Themes: blue, green, dark-blue
        self.root = root
        self.root.title(f"Frame2IMG v{__version__} — Video Frame Extractor")
        self.root.geometry("700x420")  # Initial size, wider for options
        # Try to set window icon (ICO on Windows; PNG fallback elsewhere)
        candidates = self._candidate_icon_paths()
        icon_ico = next(
            (p for p in candidates if p.lower().endswith(".ico") and os.path.exists(p)),
            None,
        )
        if icon_ico:
            try:
                self.root.iconbitmap(icon_ico)
            except tk.TclError:
                icon_ico = None  # fall through to PNG
        if not icon_ico:
            icon_png = next(
                (p for p in candidates if p.lower().endswith(".png") and os.path.exists(p)),
                None,
            )
            if icon_png:
                try:
                    _img = tk.PhotoImage(file=icon_png)
                    self.root.iconphoto(True, _img)
                    self._icon_image_ref = _img  # prevent GC
                except tk.TclError:
                    pass

        # Close handling
        self._close_after_cancel = False
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        # Top-right help button ("?")
        header_bar = customtkinter.CTkFrame(self.root, fg_color="transparent")
        header_bar.pack(fill="x", padx=10, pady=(5, 0))
        help_btn = customtkinter.CTkButton(
            header_bar,
            text="?",
            width=28,
            command=self._show_about,
        )
        help_btn.pack(side=tk.RIGHT)
        self._bind_tooltip(help_btn, "About and License")

        # --- UI Elements ---

        # Frame for input video selection
        input_frame = customtkinter.CTkFrame(self.root)
        input_frame.pack(padx=10, pady=10, fill="x")

        self.video_path_label = customtkinter.CTkLabel(input_frame, text="No video selected")
        self.video_path_label.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.select_video_button = customtkinter.CTkButton(
            input_frame, text="Select Video", command=self.select_video_file
        )
        self.select_video_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Frame for output folder selection
        output_frame = customtkinter.CTkFrame(self.root)
        output_frame.pack(padx=10, pady=5, fill="x")

        self.output_path_label = customtkinter.CTkLabel(output_frame, text="No folder selected")
        self.output_path_label.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.select_output_button = customtkinter.CTkButton(
            output_frame, text="Select Folder", command=self.select_output_folder
        )
        self.select_output_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Frame for controls
        control_frame = customtkinter.CTkFrame(self.root, fg_color="transparent")  # Transparent bg
        control_frame.pack(padx=10, pady=10, fill="x")

        self.start_button = customtkinter.CTkButton(
            control_frame, text="Start Processing", command=self.start_processing, state=tk.DISABLED
        )
        self.start_button.pack(side=tk.LEFT, pady=5)  # Pack next to the label

        # Cancel button (enabled only while processing)
        self.cancel_button = customtkinter.CTkButton(
            control_frame,
            text="Cancel",
            command=self.cancel_processing,
            state=tk.DISABLED,
        )
        self.cancel_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Open output folder button
        self.open_output_button = customtkinter.CTkButton(
            control_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            state=tk.DISABLED,
        )
        self.open_output_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Minimal UI by design; format fixed to PNG and naming is fixed.

        # Progress bar (determinate when total frames known, indeterminate otherwise)
        self.progress_bar = customtkinter.CTkProgressBar(control_frame, mode="determinate")
        self.progress_bar.pack(padx=5, pady=(10, 0), fill="x")
        self.progress_bar.set(0)

        # Status Label (placed at the bottom)
        self.status_label = customtkinter.CTkLabel(self.root, text="Status: Ready")
        self.status_label.pack(padx=10, pady=10, side=tk.BOTTOM, fill="x")

        # Variables to store paths
        self.video_file_path = ""
        self.output_folder_path = ""
        self.total_frames = None  # Will hold int when known
        self.cancel_event = None  # Set when processing to allow cancellation
        # Initialize attributes that are later set in start_processing()
        # This quiets lint about attributes defined outside __init__.
        self.filename_prefix_current = "frame_"
        self.skip_existing_current = False
        self.name_pad = 5

    def select_video_file(self):
        """Open a dialog to select the input video file."""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=(
                ("Video files", "*.mp4;*.mkv;*.webm;*.mov;*.avi;*.wmv;*.flv"),
                ("All files", "*.*"),
            ),
        )
        if file_path:
            self.video_file_path = file_path
            self.video_path_label.configure(text=self.video_file_path)
            video_name = os.path.basename(self.video_file_path)
            self.status_label.configure(text=f"Video: {video_name}")
        else:
            self.video_file_path = ""  # Clear path if selection cancelled
            self.video_path_label.configure(text="No video selected")
            self.status_label.configure(text="Status: Video selection cancelled")
        # Reset progress UI on new selection
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.cancel_button.configure(state=tk.DISABLED)
        self.open_output_button.configure(state=tk.DISABLED)
        self.update_start_button_state()

    def select_output_folder(self):
        """Open a dialog to select the output folder."""
        folder_path = filedialog.askdirectory(title="Select Output Folder")
        if folder_path:
            self.output_folder_path = folder_path
            self.output_path_label.configure(text=self.output_folder_path)
            self.status_label.configure(text=f"Output: {self.output_folder_path}")
        else:
            # Option C: keep previous path and label if selection is cancelled
            prev = getattr(self, "output_folder_path", "")
            if prev:
                self.status_label.configure(
                    text=f"Status: Output folder selection cancelled (kept: {prev})"
                )
            else:
                self.output_path_label.configure(text="No folder selected")
                self.status_label.configure(text="Status: Output folder selection cancelled")
        # Reset progress UI on new selection
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0)
        self.cancel_button.configure(state=tk.DISABLED)
        self.open_output_button.configure(state=tk.DISABLED)
        self.update_start_button_state()

    def _update_status(self, text):
        """Helper function to update status label from any thread."""
        self.status_label.configure(text=text)

    def _enable_start_button(self):
        """Helper function to enable start button from any thread."""
        self.update_start_button_state()

    def _bind_tooltip(self, widget, text: str):
        """Bind a simple hover tooltip to a widget."""

        def enter(_event):
            tw = getattr(widget, "tooltip_window", None)
            if tw:
                return
            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)
            x = widget.winfo_rootx() + 20
            y = widget.winfo_rooty() + widget.winfo_height() + 10
            tw.wm_geometry(f"+{x}+{y}")
            lbl = tk.Label(
                tw,
                text=text,
                justify=tk.LEFT,
                background="#ffffe0",
                relief=tk.SOLID,
                borderwidth=1,
                padx=6,
                pady=3,
            )
            lbl.pack()
            widget.tooltip_window = tw  # type: ignore[attr-defined]

        def leave(_event):
            tw = getattr(widget, "tooltip_window", None)
            if tw:
                tw.destroy()
                widget.tooltip_window = None  # type: ignore[attr-defined]

        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _show_about(self):
        """Show an About dialog (toplevel) with version and license button."""
        win = customtkinter.CTkToplevel(self.root)
        win.title("About Frame2IMG")
        win.resizable(False, False)
        # Make modal-ish
        try:
            win.grab_set()
        except tk.TclError:
            # Not critical if grab fails (e.g., on some window managers)
            pass

        info = (
            f"Frame2IMG v{__version__}\n\n"
            "Minimal FFmpeg-only frame extractor (PNG)\n"
            "Automatic orientation correction (when metadata is present)\n\n"
            "Bundled FFmpeg and FFprobe — see Third-party Licenses\n\n"
            "License: MIT"
        )
        content = customtkinter.CTkFrame(win, fg_color="transparent")
        content.pack(padx=20, pady=20)
        lbl = customtkinter.CTkLabel(content, text=info, justify="left")
        lbl.pack(anchor="w")

        btn_row = customtkinter.CTkFrame(content, fg_color="transparent")
        btn_row.pack(pady=(10, 0), fill="x")
        lic_btn = customtkinter.CTkButton(
            btn_row, text="View License", command=self._show_license_dialog
        )
        lic_btn.pack(side=tk.LEFT)
        tp_btn = customtkinter.CTkButton(
            btn_row, text="Third-party Licenses", command=self._show_third_party_dialog
        )
        tp_btn.pack(side=tk.LEFT, padx=(10, 0))
        close_btn = customtkinter.CTkButton(btn_row, text="Close", command=win.destroy)
        close_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Center the dialog over the root
        win.update_idletasks()
        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (win.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (win.winfo_height() // 2)
            win.geometry(f"+{x}+{y}")
        except tk.TclError:
            # If geometry queries fail, it's safe to skip centering
            pass

    def _candidate_icon_paths(self):
        """Return candidate paths for app icon files (ICO preferred, then PNG)."""
        paths = []
        # When frozen by PyInstaller, prefer EXE directory and bundled temp dir
        if getattr(sys, "frozen", False):  # type: ignore[attr-defined]
            exe_dir = os.path.dirname(sys.executable)
            paths.append(os.path.join(exe_dir, "icon.ico"))
            paths.append(os.path.join(exe_dir, "icon.png"))
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                paths.append(os.path.join(meipass, "icon.ico"))
                paths.append(os.path.join(meipass, "icon.png"))
        # Always include source directory fallback
        src_dir = os.path.dirname(os.path.abspath(__file__))
        paths.append(os.path.join(src_dir, "icon.ico"))
        paths.append(os.path.join(src_dir, "icon.png"))
        return paths

    def _candidate_license_paths(self):
        """Return candidate paths where LICENSE may reside (EXE dir, bundle, source dir)."""
        paths = []
        # When frozen by PyInstaller, prefer EXE directory and bundled temp dir
        if getattr(sys, "frozen", False):  # type: ignore[attr-defined]
            exe_dir = os.path.dirname(sys.executable)
            paths.append(os.path.join(exe_dir, "LICENSE"))
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                paths.append(os.path.join(meipass, "LICENSE"))
        # Always include source directory fallback
        src_dir = os.path.dirname(os.path.abspath(__file__))
        paths.append(os.path.join(src_dir, "LICENSE"))
        return paths

    def _get_license_text(self) -> str:
        """Return the LICENSE text; fallback to embedded MIT text if file missing/unreadable."""
        for lic_path in self._candidate_license_paths():
            try:
                with open(lic_path, encoding="utf-8") as f:
                    return f.read()
            except OSError:
                continue
        return MIT_LICENSE_FALLBACK

    def _show_license_dialog(self):
        """Show an embedded license viewer window with scrollable text."""
        win = customtkinter.CTkToplevel(self.root)
        win.title("License — Frame2IMG")
        # Provide a reasonable default size for reading
        try:
            win.geometry("760x520")
        except tk.TclError:
            pass
        try:
            win.grab_set()
        except tk.TclError:
            pass

        container = customtkinter.CTkFrame(win, fg_color="transparent")
        container.pack(padx=14, pady=14, fill="both", expand=True)

        # Scrollable text area
        text_box = customtkinter.CTkTextbox(container, wrap="word")
        text_box.pack(fill="both", expand=True)
        text_box.insert("1.0", self._get_license_text())
        text_box.configure(state="disabled")

        btn_row = customtkinter.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))
        open_file_btn = customtkinter.CTkButton(
            btn_row,
            text="Open LICENSE file",
            command=self._open_license,
        )
        open_file_btn.pack(side=tk.LEFT)
        close_btn = customtkinter.CTkButton(btn_row, text="Close", command=win.destroy)
        close_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Center relative to root
        win.update_idletasks()
        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (win.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (win.winfo_height() // 2)
            win.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _candidate_third_party_paths(self):
        """Return candidate paths for Third-party licenses (e.g., FFmpeg notice)."""
        paths = []
        if getattr(sys, "frozen", False):  # type: ignore[attr-defined]
            exe_dir = os.path.dirname(sys.executable)
            paths.append(os.path.join(exe_dir, "licenses", "FFmpeg-LGPL.txt"))
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                paths.append(os.path.join(meipass, "licenses", "FFmpeg-LGPL.txt"))
        src_dir = os.path.dirname(os.path.abspath(__file__))
        paths.append(os.path.join(src_dir, "licenses", "FFmpeg-LGPL.txt"))
        return paths

    def _get_third_party_text(self) -> str:
        """Read Third-party notice text; fallback to a brief FFmpeg note."""
        for p in self._candidate_third_party_paths():
            try:
                with open(p, encoding="utf-8") as f:
                    return f.read()
            except OSError:
                continue
        return (
            "Third-party components used by Frame2IMG\n\n"
            "FFmpeg and ffprobe from the FFmpeg project are bundled.\n"
            "Frame extraction uses FFmpeg; metadata reading may use ffprobe.\n"
            "License: LGPL v2.1 or later\n"
            "More info: https://ffmpeg.org/legal.html\n"
        )

    def _show_third_party_dialog(self):
        """Show a dialog listing third-party components and their licenses."""
        win = customtkinter.CTkToplevel(self.root)
        win.title("Third-party Licenses — Frame2IMG")
        try:
            win.geometry("760x520")
        except tk.TclError:
            pass
        try:
            win.grab_set()
        except tk.TclError:
            pass

        container = customtkinter.CTkFrame(win, fg_color="transparent")
        container.pack(padx=14, pady=14, fill="both", expand=True)

        text_box = customtkinter.CTkTextbox(container, wrap="word")
        text_box.pack(fill="both", expand=True)
        text_box.insert("1.0", self._get_third_party_text())
        text_box.configure(state="disabled")

        btn_row = customtkinter.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(8, 0))
        close_btn = customtkinter.CTkButton(btn_row, text="Close", command=win.destroy)
        close_btn.pack(side=tk.LEFT)

        win.update_idletasks()
        try:
            x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (win.winfo_width() // 2)
            y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (win.winfo_height() // 2)
            win.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass

    def _open_license(self):
        """Open the LICENSE file with the default system viewer."""
        # Try candidates in order
        for lic_path in self._candidate_license_paths():
            if os.path.exists(lic_path):
                try:
                    if os.name == "nt":
                        os.startfile(lic_path)  # type: ignore[attr-defined]
                    elif sys.platform == "darwin":
                        subprocess.Popen(["open", lic_path])
                    else:
                        subprocess.Popen(["xdg-open", lic_path])
                except OSError as e:
                    messagebox.showerror("License", f"Error opening LICENSE: {e}")
                return
        messagebox.showwarning(
            "License", "LICENSE file not found. Use the embedded viewer in About."
        )

    def _ffmpeg_path(self) -> str:
        """Return a usable ffmpeg executable path.
        Priority: env FFMPEG_PATH -> bundled locations -> PATH -> 'ffmpeg'
        """
        # 1) Explicit env var
        env_p = os.environ.get("FFMPEG_PATH")
        if env_p and os.path.isfile(env_p):
            return env_p
        # 2) Bundled candidates (PyInstaller or source tree)
        candidates = []
        exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
        try:
            if getattr(sys, "frozen", False):  # type: ignore[attr-defined]
                meipass = getattr(sys, "_MEIPASS", None)
                exe_dir = os.path.dirname(sys.executable)
                base_paths = []
                if meipass:
                    base_paths.extend([meipass, os.path.join(meipass, "bin")])
                base_paths.extend([exe_dir, os.path.join(exe_dir, "bin")])
            else:
                here = os.path.dirname(os.path.abspath(__file__))
                base_paths = [here, os.path.join(here, "bin")]
            for d in base_paths:
                if d:
                    candidates.append(os.path.join(d, exe_name))
        except Exception:
            pass
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        # 3) PATH
        which = shutil.which("ffmpeg")
        if which:
            return which
        # 4) Fallback
        return "ffmpeg"

    def _run_ffmpeg_extraction(self) -> tuple[bool, str]:
        """Extract frames using ffmpeg. Returns (ok, error_message)."""
        ffmpeg = self._ffmpeg_path()
        # Build output pattern
        pad = int(getattr(self, "name_pad", 5))
        prefix = getattr(self, "filename_prefix_current", "frame_")
        pattern = f"{prefix}%0{pad}d.png"
        out_path = os.path.join(self.output_folder_path, pattern)

        # Overwrite behavior
        overwrite_flag = "-y"  # Always overwrite for simplest flow

        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            overwrite_flag,
            "-i",
            self.video_file_path,
            "-start_number",
            "0",
            out_path,
        ]

        # Launch FFmpeg and allow cancellation
        try:
            self.root.after(0, lambda: self._update_status("Status: Processing with FFmpeg..."))
            proc = subprocess.Popen(cmd)
            # Poll loop to support cancel
            while True:
                ret = proc.poll()
                if ret is not None:
                    break
                if self.cancel_event is not None and self.cancel_event.is_set():
                    # Terminate FFmpeg cleanly; force kill if needed
                    try:
                        proc.terminate()
                    except Exception:
                        pass
                    try:
                        proc.wait(timeout=3)
                    except Exception:
                        try:
                            proc.kill()
                        except Exception:
                            pass
                    self.root.after(0, lambda: self._update_status("Status: Cancelled."))
                    return True, ""
                time.sleep(0.1)

            if ret == 0:
                # Count saved frames for a nicer status
                saved = 0
                try:
                    files = [
                        f
                        for f in os.listdir(self.output_folder_path)
                        if f.startswith(prefix) and f.lower().endswith(".png")
                    ]
                    saved = len(files)
                except Exception:
                    pass
                if saved > 0:
                    msg = f"Status: Done! Saved {saved} frames to {self.output_folder_path}"
                else:
                    msg = "Status: Done (FFmpeg)"
                self.root.after(0, lambda text=msg: self._update_status(text))
                try:
                    self.root.after(0, lambda: self.open_output_button.configure(state=tk.NORMAL))
                except Exception:
                    pass
                return True, ""
            return False, f"FFmpeg failed with code {ret}"
        except OSError as e:
            return False, f"FFmpeg not found or error: {e}"

    def _threaded_start_processing(self):
        """Actual frame extraction logic to be run in a separate thread (FFmpeg only)."""
        try:
            ok, err = self._run_ffmpeg_extraction()
            if not ok:
                self.root.after(0, lambda text=f"Status: Error - {err}": self._update_status(text))
        except Exception as e:
            err_text = f"Status: Error - {e}"
            self.root.after(0, lambda text=err_text: self._update_status(text))
        finally:
            # Stop indeterminate animation if running
            self.root.after(0, self.progress_bar.stop)
            # Re-enable/disable relevant controls
            self.root.after(0, self._enable_start_button)
            self.root.after(0, lambda: self.cancel_button.configure(state=tk.DISABLED))
            self.root.after(0, lambda: self.select_video_button.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.select_output_button.configure(state=tk.NORMAL))
            # No extra controls to re-enable in minimal UI
            # cleanup event
            self.cancel_event = None
            # If user requested close during processing, close now
            if getattr(self, "_close_after_cancel", False):
                self.root.after(0, self.root.destroy)

    def open_output_folder(self):
        """Open the output folder in the system file explorer."""
        if not self.output_folder_path:
            self.status_label.configure(text="Status: No output folder selected.")
            return
        try:
            path = self.output_folder_path
            if os.name == "nt":
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except OSError as e:
            self.status_label.configure(text=f"Status: Error opening folder - {e}")

    def start_processing(self):
        """Initiates frame extraction in a new thread."""
        if not self.video_file_path or not self.output_folder_path:
            self.status_label.configure(text="Status: Error - Video or output folder not selected.")
            return

        # Validate output folder writability
        try:
            test_path = os.path.join(self.output_folder_path, ".frame2img_write_test.tmp")
            with open(test_path, "wb") as f:
                f.write(b"0")
            os.remove(test_path)
        except OSError as e:
            self.status_label.configure(text=f"Status: Error - Output folder not writable: {e}")
            return

        self.status_label.configure(text="Status: Processing...")
        self.start_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        # Disable inputs while processing
        self.select_video_button.configure(state=tk.DISABLED)
        self.select_output_button.configure(state=tk.DISABLED)
        self.open_output_button.configure(state=tk.DISABLED)

        # Prepare cancellation event
        self.cancel_event = threading.Event()

        # Always extract every frame
        self.frame_interval = 1

        # Minimal naming settings
        self.output_format_current = "PNG"  # informational only
        self.filename_prefix_current = "frame_"
        self.name_pad = 5
        self.skip_existing_current = False

        # FFmpeg progress is not tracked numerically; use indeterminate animation
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        # Create and start the processing thread
        thread = threading.Thread(target=self._threaded_start_processing, daemon=True)
        thread.start()

    def cancel_processing(self):
        """Signal the background thread to cancel processing."""
        if self.cancel_event is not None and not self.cancel_event.is_set():
            if not messagebox.askyesno("Cancel", "Cancel processing?"):
                return
            self.cancel_event.set()
            self.status_label.configure(text="Status: Cancelling...")

    def _on_close(self):
        """Handle window close; confirm if processing is active."""
        if self.cancel_event is not None and not self.cancel_event.is_set():
            if messagebox.askyesno("Exit", "Processing is in progress. Cancel and close the app?"):
                self._close_after_cancel = True
                self.cancel_event.set()
                self.status_label.configure(text="Status: Cancelling...")
            return
        self.root.destroy()

    def update_start_button_state(self):
        """Enable or disable the start button based on path selections."""
        if self.video_file_path and self.output_folder_path:
            self.start_button.configure(state=tk.NORMAL)
        else:
            self.start_button.configure(state=tk.DISABLED)


if __name__ == "__main__":
    app_root = customtkinter.CTk()
    app = FrameExtractorApp(app_root)
    app_root.mainloop()
