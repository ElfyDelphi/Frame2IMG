"""Video Frame Extractor GUI application using customtkinter and OpenCV."""
import os
import sys
import threading
import subprocess
import tkinter as tk  # For filedialog
from tkinter import filedialog, messagebox
import customtkinter
import cv2  # pylint: disable=import-error

__version__ = "1.0.0"

# Embedded fallback MIT license text (used if LICENSE file cannot be read)
MIT_LICENSE_FALLBACK = (
    "MIT License\n\n"
    "Copyright (c) 2025 ElfyDelphi\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
    "of this software and associated documentation files (the \"Software\"), to deal\n"
    "in the Software without restriction, including without limitation the rights\n"
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
    "copies of the Software, and to permit persons to whom the Software is\n"
    "furnished to do so, subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all\n"
    "copies or substantial portions of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
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
        self.root.geometry("700x420") # Initial size, wider for options
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

        # self.total_frames_label will be in control_frame now

        self.select_video_button = customtkinter.CTkButton(input_frame, text="Select Video",
                                                           command=self.select_video_file)
        self.select_video_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Frame for output folder selection
        output_frame = customtkinter.CTkFrame(self.root)
        output_frame.pack(padx=10, pady=5, fill="x")

        self.output_path_label = customtkinter.CTkLabel(output_frame, text="No folder selected")
        self.output_path_label.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill="x")

        self.select_output_button = customtkinter.CTkButton(output_frame, text="Select Folder",
                                                            command=self.select_output_folder)
        self.select_output_button.pack(side=tk.RIGHT, padx=5, pady=5)

        # Frame for controls
        control_frame = customtkinter.CTkFrame(self.root, fg_color="transparent") # Transparent bg
        control_frame.pack(padx=10, pady=10, fill="x")

        self.total_frames_label = customtkinter.CTkLabel(control_frame, text="Total Frames: N/A")
        self.total_frames_label.pack(side=tk.LEFT, padx=(0, 20), pady=5) # Right padding

        self.start_button = customtkinter.CTkButton(control_frame,
                                                      text="Start Processing",
                                                      command=self.start_processing,
                                                      state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, pady=5) # Pack next to the label

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

        # Options row for format and naming
        options_row = customtkinter.CTkFrame(control_frame, fg_color="transparent")
        options_row.pack(padx=0, pady=(5, 0), fill="x")

        # Format is fixed to PNG (lossless)
        options_format_label = customtkinter.CTkLabel(options_row, text="Format: PNG")
        options_format_label.pack(side=tk.LEFT, padx=(0, 20))

        # Filename prefix
        options_prefix_label = customtkinter.CTkLabel(options_row, text="Prefix:")
        options_prefix_label.pack(side=tk.LEFT, padx=(20, 5))
        self.prefix_var = tk.StringVar(value="frame_")
        self.prefix_entry = customtkinter.CTkEntry(options_row, width=120, textvariable=self.prefix_var)
        self.prefix_entry.pack(side=tk.LEFT, padx=(0, 20))

        # Skip existing files
        self.skip_existing_var = tk.BooleanVar(value=False)
        self.skip_existing_checkbox = customtkinter.CTkCheckBox(
            options_row,
            text="Skip existing",
            variable=self.skip_existing_var,
            command=self._on_toggle_skip_existing,
        )
        self.skip_existing_checkbox.pack(side=tk.LEFT)
        # Tooltip for skip existing
        self._bind_tooltip(
            self.skip_existing_checkbox,
            "When enabled, filenames use the source frame index and "
            "existing files are skipped (no overwrite).",
        )

        # Zero-padding digits
        options_digits_label = customtkinter.CTkLabel(options_row, text="Digits:")
        options_digits_label.pack(side=tk.LEFT, padx=(20, 5))
        self.digits_var = tk.StringVar(value="5")
        self.digits_entry = customtkinter.CTkEntry(options_row, width=60, textvariable=self.digits_var)
        self.digits_entry.pack(side=tk.LEFT)
        # Tooltip for digits
        self._bind_tooltip(
            self.digits_entry,
            "Zero-padding digits (1–12). Default is 5; "
            "becomes 6 when 'Skip existing' is enabled."
        )
        # Track if user manually edited digits (prevents auto-bump overrides)
        self._digits_user_changed = False
        # Live input validation: allow only digits while typing (empty allowed)
        self._digits_trace_updating = False
        self.digits_var.trace_add("write", self._on_digits_var_changed)
        # Mark user-changed on keypress; clamp to range on focus-out
        self.digits_entry.bind("<KeyRelease>", lambda _e: self._mark_digits_user_changed())
        self.digits_entry.bind("<FocusOut>", self._on_digits_focus_out)

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
        self.frame_interval = 1
        self.output_format_current = 'PNG'
        self.filename_prefix_current = 'frame_'
        self.skip_existing_current = False
        self.name_pad = 5


    def select_video_file(self):
        """Open a dialog to select the input video file."""
        file_path = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=(
                ("Video files",
                 "*.mp4;*.mkv;*.webm;*.mov;"
                 "*.avi;*.wmv;*.flv"),
                ("All files", "*.*"),
            ),
        )
        if file_path:
            self.video_file_path = file_path
            self.video_path_label.configure(text=self.video_file_path)
            # Try to get total frames
            try:
                # pylint: disable=no-member
                cap = cv2.VideoCapture(self.video_file_path)
                if cap.isOpened():
                    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    # Some codecs may report 0; treat non-positive as unknown
                    self.total_frames = total_frames if total_frames > 0 else None
                    video_name = os.path.basename(self.video_file_path)
                    if self.total_frames is not None:
                        self.total_frames_label.configure(text=f"Total Frames: {self.total_frames}")
                        status_text = f"Video: {video_name} ({self.total_frames} frames)"
                    else:
                        self.total_frames_label.configure(text="Total Frames: Unknown")
                        status_text = f"Video: {video_name} (unknown frames)"
                    self.status_label.configure(text=status_text)
                    cap.release()
                else:
                    self.total_frames_label.configure(text="Total Frames: Error")
                    self.status_label.configure(text="Status: Error opening video for frame count.")
                    self.total_frames = None
                    cap.release()
            except (OSError, IOError, ValueError) as e_fs:
                self.total_frames_label.configure(text="Total Frames: Error")
                error_message = f"Status: File error - {str(e_fs)}"
                self.status_label.configure(text=error_message)
                self.total_frames = None
            except cv2.error as e_gen:  # pylint: disable=catching-non-exception
                self.total_frames_label.configure(text="Total Frames: Error")
                error_message = f"Status: Error reading video details - {str(e_gen)}"
                self.status_label.configure(text=error_message)
                self.total_frames = None

        else:
            self.video_file_path = "" # Clear path if selection cancelled
            self.video_path_label.configure(text="No video selected")
            self.total_frames_label.configure(text="Total Frames: N/A")
            self.status_label.configure(text="Status: Video selection cancelled")
            self.total_frames = None
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

    def _mark_digits_user_changed(self):
        """Mark that the user manually edited the digits field."""
        self._digits_user_changed = True

    def _on_digits_var_changed(self, *_):
        """Keep digits-only in the input while allowing empty during typing."""
        if getattr(self, "_digits_trace_updating", False):
            return
        val = self.digits_var.get()
        # Allow empty string while typing
        if val == "":
            return
        filtered = "".join(ch for ch in val if ch.isdigit())
        if filtered != val:
            self._digits_trace_updating = True
            try:
                self.digits_var.set(filtered)
            finally:
                self._digits_trace_updating = False

    def _on_digits_focus_out(self, _event=None):
        """On blur: clamp to 1–12; if empty/invalid, set to default (6 if skip-existing else 5)."""
        self._mark_digits_user_changed()
        s = (self.digits_var.get() or "").strip()
        # Default on empty
        if s == "":
            default_val = (
                "6"
                if (hasattr(self, 'skip_existing_var') and bool(self.skip_existing_var.get()))
                else "5"
            )
            self.digits_var.set(default_val)
            return
        try:
            v = int(s)
        except (ValueError, TypeError):
            default_val = "6" if (hasattr(self, 'skip_existing_var') and bool(self.skip_existing_var.get())) else "5"
            self.digits_var.set(default_val)
            return
        # Clamp to 1–12
        if v < 1:
            v = 1
        elif v > 12:
            v = 12
        self.digits_var.set(str(v))

    def _on_toggle_skip_existing(self):
        """Auto-bump digits to 6 when enabling skip existing, unless user changed it."""
        if bool(self.skip_existing_var.get()):
            # Only adjust if user hasn't explicitly changed digits
            if not getattr(self, "_digits_user_changed", False):
                try:
                    cur = int(self.digits_var.get())
                except (ValueError, TypeError):
                    cur = 0
                if cur < 6:
                    self.digits_var.set("6")

    def _bind_tooltip(self, widget, text: str):
        """Bind a simple hover tooltip to a widget."""
        def enter(_event):
            tw = getattr(widget, "_tipwindow", None)
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
            setattr(widget, "_tipwindow", tw)
        def leave(_event):
            tw = getattr(widget, "_tipwindow", None)
            if tw:
                tw.destroy()
                setattr(widget, "_tipwindow", None)
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
            "Video Frame Extractor (PNG-only)\n"
            "Dark theme UI with CustomTkinter\n\n"
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
                with open(lic_path, "r", encoding="utf-8") as f:
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
        open_file_btn = customtkinter.CTkButton(btn_row, text="Open LICENSE file", command=self._open_license)
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

    def _open_license(self):
        """Open the LICENSE file with the default system viewer."""
        # Try candidates in order
        for lic_path in self._candidate_license_paths():
            if os.path.exists(lic_path):
                try:
                    if os.name == 'nt':
                        os.startfile(lic_path)  # type: ignore[attr-defined]
                    elif sys.platform == 'darwin':
                        subprocess.Popen(['open', lic_path])
                    else:
                        subprocess.Popen(['xdg-open', lic_path])
                except OSError as e:
                    messagebox.showerror("License", f"Error opening LICENSE: {e}")
                return
        messagebox.showwarning("License", "LICENSE file not found. Use the embedded viewer in About.")

    def _sanitize_prefix(self, prefix: str) -> str:
        """Sanitize filename prefix by removing invalid path characters.
        Returns a safe default if the result is empty.
        """
        if not isinstance(prefix, str):
            return "frame_"
        s = prefix.strip()
        # Replace characters invalid on Windows and common platforms
        invalid = '<>:"/\\|?*\n\r\t'
        trans = str.maketrans({ch: '_' for ch in invalid})
        s = s.translate(trans)
        return s if s else "frame_"

    def _threaded_start_processing(self):
        """Actual frame extraction logic to be run in a separate thread."""
        video_capture = None
        try:
            # pylint: disable=no-member
            video_capture = cv2.VideoCapture(self.video_file_path)
            if not video_capture.isOpened():
                self.root.after(
                    0,
                    lambda: self._update_status("Status: Error - Could not open video file."),
                )
                self.root.after(0, self._enable_start_button)
                self.root.after(
                    0,
                    lambda: self.cancel_button.configure(state=tk.DISABLED),
                )
                self.root.after(0, self.progress_bar.stop)
                return

            # Track processed frames (for progress) and saved frames (for filenames)
            error_message = None
            frame_index = 0  # 0-based index of processed frames
            saved_count = 0  # number of frames saved
            success, image = video_capture.read()

            while success:
                # Check for cancellation request
                if self.cancel_event is not None and self.cancel_event.is_set():
                    break
                # Save according to interval
                if frame_index % max(getattr(self, 'frame_interval', 1), 1) == 0:
                    # Always write PNG
                    filename_ext = 'png'
                    pad = int(getattr(self, 'name_pad', 5))
                    prefix = getattr(self, 'filename_prefix_current', 'frame_')
                    index_for_name = (
                        frame_index
                        if bool(getattr(self, 'skip_existing_current', False))
                        else saved_count
                    )
                    name_formatted = f"{prefix}{index_for_name:0{pad}d}.{filename_ext}"
                    frame_filename = os.path.join(self.output_folder_path, name_formatted)
                    if (
                        bool(getattr(self, 'skip_existing_current', False))
                        and os.path.exists(frame_filename)
                    ):
                        pass
                    else:
                        try:
                            ok = cv2.imwrite(frame_filename, image)  # pylint: disable=no-member
                        except (cv2.error, OSError) as e_write:  # pylint: disable=catching-non-exception
                            ok = False
                            error_message = f"Status: File write error - {str(e_write)}"
                        if not ok:
                            if error_message is None:
                                error_message = f"Status: Error writing file: {os.path.basename(frame_filename)}"
                            break
                        saved_count += 1
                # Update status every 30 saved frames
                if saved_count > 0 and saved_count % 30 == 0:
                    status_update_text = f"Status: Processing... Saved {saved_count} frames"
                    self.root.after(0, lambda text=status_update_text: self._update_status(text))
                # Update progress periodically based on processed frames
                if self.total_frames and frame_index % 20 == 0:
                    progress_value = min((frame_index + 1) / float(self.total_frames), 1.0)
                    self.root.after(0, lambda v=progress_value: self.progress_bar.set(v))
                # Periodic processed-frame status updates
                if self.total_frames and frame_index > 0 and frame_index % 200 == 0:
                    pct = min(((frame_index + 1) / float(self.total_frames)) * 100.0, 100.0)
                    processed_text = (
                        f"Status: Processing... Processed {frame_index + 1}/{self.total_frames} "
                        f"(~{pct:.1f}%) — Saved {saved_count}"
                    )
                    self.root.after(0, lambda text=processed_text: self._update_status(text))
                elif not self.total_frames and frame_index > 0 and frame_index % 500 == 0:
                    processed_text = (
                        f"Status: Processing... Processed {frame_index + 1} — Saved {saved_count}"
                    )
                    self.root.after(0, lambda text=processed_text: self._update_status(text))
                success, image = video_capture.read()
                frame_index += 1

            video_capture.release()
            video_capture = None
            if error_message:
                self.root.after(0, lambda text=error_message: self._update_status(text))
                if saved_count > 0:
                    self.root.after(
                        0,
                        lambda: self.open_output_button.configure(state=tk.NORMAL),
                    )
            elif self.cancel_event is not None and self.cancel_event.is_set():
                cancel_text = f"Status: Cancelled. Saved {saved_count} frames to {self.output_folder_path}"
                self.root.after(0, lambda text=cancel_text: self._update_status(text))
                if saved_count > 0:
                    self.root.after(
                        0,
                        lambda: self.open_output_button.configure(state=tk.NORMAL),
                    )
            else:
                final_status_text = (
                    f"Status: Done! Saved {saved_count} frames to {self.output_folder_path}"
                )
                self.root.after(0, lambda text=final_status_text: self._update_status(text))
                if self.total_frames:
                    # Ensure progress bar shows completion
                    self.root.after(0, lambda: self.progress_bar.set(1.0))
                if saved_count > 0:
                    self.root.after(
                        0,
                        lambda: self.open_output_button.configure(state=tk.NORMAL),
                    )
        except (OSError, IOError) as e_io:
            io_error_text = (
                "Status: File Error - "
                f"{str(e_io)}"
            )
            self.root.after(0, lambda text=io_error_text: self._update_status(text))
        except cv2.error as e:  # pylint: disable=catching-non-exception
            general_error_text = (
                "Status: Error - "
                f"{str(e)}"
            )
            self.root.after(0, lambda text=general_error_text: self._update_status(text))
        finally:
            # Ensure capture is released even on early exit or exception
            if 'video_capture' in locals() and video_capture is not None:
                video_capture.release()
            # Stop indeterminate animation if running
            self.root.after(0, self.progress_bar.stop)
            # Re-enable/disable relevant controls
            self.root.after(0, self._enable_start_button)
            self.root.after(0, lambda: self.cancel_button.configure(state=tk.DISABLED))
            self.root.after(0, lambda: self.select_video_button.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.select_output_button.configure(state=tk.NORMAL))
            # Format is fixed; no control to re-enable
            if hasattr(self, 'prefix_entry'):
                self.root.after(0, lambda: self.prefix_entry.configure(state=tk.NORMAL))
            if hasattr(self, 'skip_existing_checkbox'):
                self.root.after(0, lambda: self.skip_existing_checkbox.configure(state=tk.NORMAL))
            if hasattr(self, 'digits_entry'):
                self.root.after(0, lambda: self.digits_entry.configure(state=tk.NORMAL))
            # cleanup event
            self.cancel_event = None
            # If user requested close during processing, close now
            if getattr(self, '_close_after_cancel', False):
                self.root.after(0, self.root.destroy)

    def open_output_folder(self):
        """Open the output folder in the system file explorer."""
        if not self.output_folder_path:
            self.status_label.configure(text="Status: No output folder selected.")
            return
        try:
            path = self.output_folder_path
            if os.name == 'nt':
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', path])
            else:
                subprocess.Popen(['xdg-open', path])
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
            self.status_label.configure(
                text=f"Status: Error - Output folder not writable: {e}"
            )
            return

        self.status_label.configure(text="Status: Processing...")
        self.start_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        # Disable inputs while processing
        self.select_video_button.configure(state=tk.DISABLED)
        self.select_output_button.configure(state=tk.DISABLED)
        self.open_output_button.configure(state=tk.DISABLED)
        if hasattr(self, 'prefix_entry'):
            self.prefix_entry.configure(state=tk.DISABLED)
        if hasattr(self, 'skip_existing_checkbox'):
            self.skip_existing_checkbox.configure(state=tk.DISABLED)
        if hasattr(self, 'digits_entry'):
            self.digits_entry.configure(state=tk.DISABLED)

        # Prepare cancellation event
        self.cancel_event = threading.Event()

        # Always extract every frame
        self.frame_interval = 1

        # Output format is fixed to PNG (lossless)
        self.output_format_current = 'PNG'

        # Filename prefix and skip-existing behavior
        raw_prefix = self.prefix_var.get() if hasattr(self, 'prefix_var') else 'frame_'
        sanitized_prefix = self._sanitize_prefix(raw_prefix)
        if not sanitized_prefix or (isinstance(raw_prefix, str) and raw_prefix.strip() == ""):
            # Default to video basename + '_' when available
            base = os.path.splitext(os.path.basename(getattr(self, 'video_file_path', '') or ''))[0]
            if base:
                derived = f"{base}_"
                sanitized_prefix = self._sanitize_prefix(derived)
        self.filename_prefix_current = sanitized_prefix if sanitized_prefix else 'frame_'
        self.skip_existing_current = bool(self.skip_existing_var.get()) if hasattr(self, 'skip_existing_var') else False
        # Determine zero-padding digits
        digits_val = None
        try:
            digits_val = int(self.digits_var.get()) if hasattr(self, 'digits_var') else None
        except (ValueError, TypeError):
            digits_val = None
        if digits_val is None or digits_val < 1 or digits_val > 12:
            digits_val = 6 if self.skip_existing_current else 5
        self.name_pad = digits_val

        # Configure progress bar based on availability of total frames
        if self.total_frames:
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)
        else:
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
