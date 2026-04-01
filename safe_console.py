import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk
import time
import threading
import queue

from modules.head_module import HeadScrollController
from modules.hands_module import HandsController

APP_NAME = "S.A.F.E"

current_controller = None
is_switching = False   # guard: block video loop and button spam during switch

report_image = None
report_imgtk = None
report_scale = 1.0

frame_queue = queue.Queue(maxsize=2)  # Non-blocking frame delivery
video_thread_running = False


# =============================
# ROOT WINDOW
# =============================

root = tk.Tk()
root.title(APP_NAME)
root.attributes("-fullscreen", True)
root.configure(bg="black")


# =============================
# BOOT SCREEN
# =============================

boot_frame = tk.Frame(root, bg="black")
boot_frame.pack(fill="both", expand=True)

boot_label = tk.Label(
    boot_frame,
    text="INITIALIZING S.A.F.E",
    font=("Courier", 40),
    fg="cyan",
    bg="black"
)
boot_label.pack(expand=True)


def animate_boot(count=0):
    dots = "." * (count % 4)
    boot_label.config(text=f"INITIALIZING S.A.F.E{dots}")

    if count < 30:
        root.after(150, animate_boot, count + 1)
    else:
        show_selection_screen()


# =============================
# SELECTION SCREEN
# =============================

def show_selection_screen():
    boot_frame.destroy()

    selection_frame = tk.Frame(root, bg="black")
    selection_frame.pack(fill="both", expand=True)

    # Title
    title = tk.Label(
        selection_frame,
        text="S.A.F.E MEDICAL SYSTEM",
        font=("Courier", 36, "bold"),
        fg="cyan",
        bg="black"
    )
    title.pack(pady=50)

    # Subtitle
    subtitle = tk.Label(
        selection_frame,
        text="SELECT CONTROL MODULE",
        font=("Courier", 24),
        fg="white",
        bg="black"
    )
    subtitle.pack(pady=20)

    # Buttons frame
    buttons_frame = tk.Frame(selection_frame, bg="black")
    buttons_frame.pack(expand=True)

    # Module options with descriptions
    modules = [
        ("H.A.N.D.S", "Hand gesture control for scrolling and zooming", "#2E7D32"),
        ("H.E.A.D", "Head movement tracking for hands-free navigation", "#1565C0"),
    ]

    for module_name, description, color in modules:
        module_frame = tk.Frame(buttons_frame, bg="black")
        module_frame.pack(pady=15)

        btn = tk.Button(
            module_frame,
            text=module_name,
            font=("Courier", 20, "bold"),
            bg=color,
            fg="white",
            width=20,
            height=2,
            cursor="hand2",
            command=lambda m=module_name: start_console_with_module(m)
        )
        btn.pack()

        desc_label = tk.Label(
            module_frame,
            text=description,
            font=("Courier", 12),
            fg="gray",
            bg="black"
        )
        desc_label.pack(pady=5)

    # Footer with instructions
    footer = tk.Label(
        selection_frame,
        text="Press ESC to exit | Select a module to begin",
        font=("Courier", 12),
        fg="gray",
        bg="black"
    )
    footer.pack(side="bottom", pady=30)

    # Bind ESC key to exit
    root.bind('<Escape>', lambda e: shutdown())


def start_console_with_module(module_name):
    """Start the main console with selected module"""
    # Clear selection screen
    for widget in root.winfo_children():
        widget.destroy()

    start_console(module_name)


# =============================
# MAIN CONSOLE
# =============================

def start_console(initial_module="H.A.N.D.S"):
    global main_frame, report_canvas, camera_label, video_thread_running

    main_frame = tk.Frame(root, bg="black")
    main_frame.pack(fill="both", expand=True)

    # Top bar with module info
    top_bar = tk.Frame(main_frame, bg="#1a1a1a", height=60)
    top_bar.pack(fill="x")
    top_bar.pack_propagate(False)

    title = tk.Label(
        top_bar,
        text="S.A.F.E MEDICAL CONSOLE",
        font=("Courier", 20, "bold"),
        fg="cyan",
        bg="#1a1a1a"
    )
    title.pack(side="left", padx=20, pady=15)

    # Active module indicator
    module_indicator = tk.Label(
        top_bar,
        text=f"ACTIVE MODULE: {initial_module}",
        font=("Courier", 12),
        fg="lime",
        bg="#1a1a1a"
    )
    module_indicator.pack(side="right", padx=20, pady=15)

    # Main content area
    content_frame = tk.Frame(main_frame, bg="black")
    content_frame.pack(fill="both", expand=True, padx=20, pady=10)

    # LEFT - Camera View
    left_panel = tk.Frame(content_frame, bg="black", relief="groove", bd=2)
    left_panel.pack(side="left", expand=True, fill="both", padx=10, pady=10)

    camera_title = tk.Label(
        left_panel,
        text="CAMERA VIEW",
        font=("Courier", 14, "bold"),
        fg="cyan",
        bg="black"
    )
    camera_title.pack(pady=10)

    camera_label = tk.Label(left_panel, bg="black", relief="sunken", bd=2)
    camera_label.pack(expand=True, padx=10, pady=10)

    # Control instructions
    control_info = tk.Label(
        left_panel,
        text="Control Instructions:\n• Wave hand to scroll\n• Pinch to zoom\n• Head movement for navigation",
        font=("Courier", 10),
        fg="gray",
        bg="black",
        justify="left"
    )
    control_info.pack(pady=10)

    # RIGHT - Report Viewer
    right_panel = tk.Frame(content_frame, bg="black", relief="groove", bd=2)
    right_panel.pack(side="right", expand=True, fill="both", padx=10, pady=10)

    report_title = tk.Label(
        right_panel,
        text="REPORT VIEWER",
        font=("Courier", 14, "bold"),
        fg="lime",
        bg="black"
    )
    report_title.pack(pady=10)

    # Report canvas with scrollbars
    report_container = tk.Frame(right_panel, bg="black")
    report_container.pack(expand=True, fill="both", padx=10, pady=10)

    scroll_y = tk.Scrollbar(report_container, orient="vertical")
    scroll_y.pack(side="right", fill="y")

    scroll_x = tk.Scrollbar(report_container, orient="horizontal")
    scroll_x.pack(side="bottom", fill="x")

    report_canvas = tk.Canvas(
        report_container,
        bg="#1a1a1a",
        width=600,
        height=500,
        highlightthickness=0,
        yscrollcommand=scroll_y.set,
        xscrollcommand=scroll_x.set
    )
    report_canvas.pack(expand=True, fill="both")

    scroll_y.config(command=report_canvas.yview)
    scroll_x.config(command=report_canvas.xview)

    # Placeholder text for report viewer
    report_canvas.create_text(
        300, 250,
        text="No report loaded\n\nClick 'UPLOAD REPORT' to begin",
        font=("Courier", 14),
        fill="gray",
        justify="center"
    )

    # Bottom Control Bar
    control_frame = tk.Frame(main_frame, bg="#1a1a1a", height=80)
    control_frame.pack(fill="x", side="bottom")
    control_frame.pack_propagate(False)

    # Module switching buttons
    module_buttons_frame = tk.Frame(control_frame, bg="#1a1a1a")
    module_buttons_frame.pack(side="left", padx=20, pady=15)

    for mod in ["H.A.N.D.S", "H.E.A.D"]:
        btn = tk.Button(
            module_buttons_frame,
            text=mod,
            font=("Courier", 12, "bold"),
            bg="#2E7D32" if mod == initial_module else "#424242",
            fg="white",
            width=12,
            cursor="hand2",
            command=lambda m=mod: switch_module(m, module_indicator)
        )
        btn.pack(side="left", padx=5)

    # Action buttons
    action_buttons_frame = tk.Frame(control_frame, bg="#1a1a1a")
    action_buttons_frame.pack(side="right", padx=20, pady=15)

    upload_btn = tk.Button(
        action_buttons_frame,
        text="📄 UPLOAD REPORT",
        font=("Courier", 12, "bold"),
        bg="#1565C0",
        fg="white",
        cursor="hand2",
        command=upload_report
    )
    upload_btn.pack(side="left", padx=5)

    exit_btn = tk.Button(
        action_buttons_frame,
        text="❌ EXIT",
        font=("Courier", 12, "bold"),
        bg="#C62828",
        fg="white",
        cursor="hand2",
        command=shutdown
    )
    exit_btn.pack(side="left", padx=5)

    # Back to selection button
    back_btn = tk.Button(
        action_buttons_frame,
        text="← BACK",
        font=("Courier", 12, "bold"),
        bg="#FF6F00",
        fg="white",
        cursor="hand2",
        command=return_to_selection
    )
    back_btn.pack(side="left", padx=5)

    # Fix: initialize module first — controllers own their cameras
    switch_module(initial_module, module_indicator)
    
    # Start background video capture thread
    video_thread_running = True
    video_thread = threading.Thread(target=video_capture_thread, daemon=True)
    video_thread.start()
    
    update_video()


def return_to_selection():
    """Return to module selection screen"""
    global current_controller, video_thread_running

    video_thread_running = False
    time.sleep(0.1)  # Allow video thread to stop

    if current_controller:
        current_controller.release()
        current_controller = None

    # Clear main window
    for widget in root.winfo_children():
        widget.destroy()

    show_selection_screen()


# =============================
# REPORT FUNCTIONS
# =============================

def upload_report():
    global report_image, report_imgtk, report_scale

    file_path = filedialog.askopenfilename(
        filetypes=[
            ("Image Files", "*.png *.jpg *.jpeg *.bmp *.tiff"),
            ("All Files", "*.*")
        ],
        title="Select Medical Report"
    )

    if file_path:
        report_scale = 1.0
        report_image = Image.open(file_path)
        report_canvas.delete("all")  # Fix: clear placeholder before render
        render_report()


def render_report():
    global report_imgtk

    if report_image is None:
        return

    new_w = int(report_image.width * report_scale)
    new_h = int(report_image.height * report_scale)

    resized = report_image.resize((new_w, new_h), Image.LANCZOS)
    report_imgtk = ImageTk.PhotoImage(resized)

    report_canvas.delete("all")
    report_canvas.create_image(0, 0, anchor="nw", image=report_imgtk)
    report_canvas.config(scrollregion=report_canvas.bbox("all"))


def zoom_report(factor):
    global report_scale
    report_scale *= factor
    # Limit zoom levels
    report_scale = max(0.1, min(5.0, report_scale))
    render_report()


def scroll_report(delta_x=0, delta_y=0):
    if report_image is None:
        return

    # Smooth scrolling with limits
    delta_x = max(-10, min(10, delta_x))
    delta_y = max(-10, min(10, delta_y))

    if delta_x != 0:
        report_canvas.xview_scroll(int(delta_x), "units")
    if delta_y != 0:
        report_canvas.yview_scroll(int(delta_y), "units")


# =============================
# MODULE SWITCHING
# =============================

def switch_module(module_name, indicator_label=None):
    """Entry point — called on the main thread from a button click."""
    global is_switching

    if is_switching:
        return  # ignore button spam while a switch is already in progress

    is_switching = True

    # Show a "SWITCHING..." overlay on the camera label immediately
    _show_switching_overlay(module_name)

    if indicator_label:
        indicator_label.config(text=f"SWITCHING TO: {module_name}…")

    # Do the blocking camera work on a background thread
    t = threading.Thread(
        target=_switch_module_worker,
        args=(module_name, indicator_label),
        daemon=True
    )
    t.start()


def _show_switching_overlay(module_name):
    """Draw a simple text frame on the camera label so the UI stays alive."""
    try:
        if camera_label is None or not camera_label.winfo_exists():
            return
        w, h = 700, 500
        import numpy as np
        blank = np.zeros((h, w, 3), dtype="uint8")
        cv2.putText(blank, f"LOADING {module_name}...", (w // 2 - 200, h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 220, 220), 2)
        rgb = cv2.cvtColor(blank, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(img)
        camera_label.imgtk = imgtk
        camera_label.configure(image=imgtk)
    except Exception:
        pass


def _switch_module_worker(module_name, indicator_label):
    """Runs on a background thread — safe to block here."""
    global current_controller

    # 1. Release the old controller (closes its camera)
    old = current_controller
    if old:
        try:
            old.release()
        except Exception as e:
            print(f"Error releasing old controller: {e}")

    # Small delay so the OS fully releases the camera device
    time.sleep(0.3)

    # 2. Build the new controller
    new_controller = None
    instructions = ""
    try:
        if module_name == "H.A.N.D.S":
            new_controller = HandsController(
                scroll_callback=scroll_report,
                zoom_callback=zoom_report
            )
            instructions = "✋ Hand Controls:\n• Left hand index → Scroll\n• Right pinch in/out → Zoom"

        elif module_name == "H.E.A.D":
            new_controller = HeadScrollController(
                zoom_callback=zoom_report,
                scroll_callback=scroll_report
            )
            instructions = "👤 Head Controls:\n• Turn head left/right → Scroll\n• Lean forward/back → Zoom"

    except Exception as e:
        print(f"Error initializing {module_name}: {e}")
        instructions = "⚠️ Module failed to load. Check camera connection."

    # 3. Hand results back to the main thread safely via root.after
    root.after(0, _apply_new_controller, new_controller, module_name, indicator_label, instructions)


def _apply_new_controller(new_controller, module_name, indicator_label, instructions):
    """Called on the main thread once the background worker finishes."""
    global current_controller, is_switching

    current_controller = new_controller
    is_switching = False

    if indicator_label:
        indicator_label.config(text=f"ACTIVE MODULE: {module_name}")

    update_control_instructions(instructions)


def update_control_instructions(text):
    """Update control instructions label in the UI"""
    try:
        for widget in root.winfo_children():
            _recursive_update_label(widget, text)
    except Exception:
        pass


def _recursive_update_label(widget, text):
    """Recursively search for the control instructions label and update it"""
    if isinstance(widget, tk.Label):
        current = str(widget.cget("text"))
        if "Control Instructions" in current or "✋" in current or "👤" in current or "⚠️" in current:
            widget.config(text=text)
            return
    for child in widget.winfo_children():
        _recursive_update_label(child, text)


# =============================
# VIDEO LOOP (Background Thread + UI Update)
# =============================

def video_capture_thread():
    """Runs on a background thread - continuously captures frames"""
    global video_thread_running
    
    while video_thread_running:
        if not is_switching and current_controller:
            try:
                frame = current_controller.get_frame()
                if frame is not None:
                    # Non-blocking queue put - drop old frames if queue is full
                    try:
                        frame_queue.put_nowait(frame)
                    except queue.Full:
                        # Queue is full, drop this frame
                        pass
            except Exception as e:
                print(f"Frame capture error: {e}")
        
        time.sleep(0.01)  # Small delay to prevent busy-waiting


def update_video():
    """Runs on the main thread - updates UI with latest frame"""
    try:
        frame = frame_queue.get_nowait()
        
        # Only update if camera_label widget still exists
        if camera_label is not None and camera_label.winfo_exists():
            frame = cv2.resize(frame, (700, 500))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            imgtk = ImageTk.PhotoImage(img)

            camera_label.imgtk = imgtk
            camera_label.configure(image=imgtk)
    except queue.Empty:
        # No new frame available, that's fine
        pass
    except Exception as e:
        print(f"UI update error: {e}")

    root.after(16, update_video)  # ~60 FPS update rate for UI


# =============================
# SHUTDOWN
# =============================

def shutdown():
    global current_controller, video_thread_running

    video_thread_running = False
    time.sleep(0.1)  # Allow video thread to stop

    if current_controller:
        current_controller.release()
        current_controller = None

    root.quit()
    root.destroy()


# Start the application
animate_boot()
root.mainloop()
