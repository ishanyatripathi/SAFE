import tkinter as tk
from tkinter import filedialog
import cv2
from PIL import Image, ImageTk
import time

from modules.head_module import HeadScrollController
from modules.iris_module import IrisController
from modules.hands_module import HandsController

APP_NAME = "S.A.F.E"

current_controller = None
default_camera = None

report_image = None
report_imgtk = None
report_scale = 1.0


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
        start_console()


# =============================
# MAIN CONSOLE
# =============================

def start_console():
    global default_camera, main_frame, report_canvas

    boot_frame.destroy()

    main_frame = tk.Frame(root, bg="black")
    main_frame.pack(fill="both", expand=True)

    title = tk.Label(
        main_frame,
        text="S.A.F.E MEDICAL CONSOLE",
        font=("Courier", 28),
        fg="cyan",
        bg="black"
    )
    title.pack(pady=10)

    panel_frame = tk.Frame(main_frame, bg="black")
    panel_frame.pack(fill="both", expand=True)

    # LEFT - Camera
    left_panel = tk.Frame(panel_frame, bg="black")
    left_panel.pack(side="left", expand=True, fill="both", padx=20, pady=10)

    global camera_label
    camera_label = tk.Label(left_panel, bg="black")
    camera_label.pack(expand=True)

    # RIGHT - Report Viewer
    right_panel = tk.Frame(panel_frame, bg="black")
    right_panel.pack(side="right", expand=True, fill="both", padx=20, pady=10)

    report_title = tk.Label(
        right_panel,
        text="REPORT VIEWER",
        font=("Courier", 18),
        fg="lime",
        bg="black"
    )
    report_title.pack(pady=10)

    report_canvas = tk.Canvas(
        right_panel,
        bg="black",
        width=600,
        height=700,
        highlightthickness=0
    )
    report_canvas.pack(expand=True)

    scroll_x = tk.Scrollbar(
        right_panel,
        orient="horizontal",
        command=report_canvas.xview
    )
    scroll_x.pack(side="bottom", fill="x")

    scroll_y = tk.Scrollbar(
        right_panel,
        orient="vertical",
        command=report_canvas.yview
    )
    scroll_y.pack(side="right", fill="y")

    report_canvas.configure(
        yscrollcommand=scroll_y.set,
        xscrollcommand=scroll_x.set
    )

    # Controls
    control_frame = tk.Frame(main_frame, bg="black")
    control_frame.pack(pady=20)

    for mod in ["H.A.N.D.S", "H.E.A.D"]:
        btn = tk.Button(
            control_frame,
            text=mod,
            font=("Courier", 16),
            bg="darkgreen",
            fg="white",
            command=lambda m=mod: switch_module(m)
        )
        btn.pack(side="left", padx=10)

    upload_btn = tk.Button(
        control_frame,
        text="UPLOAD REPORT",
        font=("Courier", 16),
        bg="blue",
        fg="white",
        command=upload_report
    )
    upload_btn.pack(side="left", padx=10)

    exit_btn = tk.Button(
        control_frame,
        text="EXIT",
        font=("Courier", 16),
        bg="darkred",
        fg="white",
        command=shutdown
    )
    exit_btn.pack(side="left", padx=10)

    default_camera = cv2.VideoCapture(0)
    update_video()


# =============================
# REPORT FUNCTIONS
# =============================

def upload_report():
    global report_image, report_imgtk, report_scale

    file_path = filedialog.askopenfilename(
        filetypes=[("Image Files", "*.png *.jpg *.jpeg")]
    )

    if file_path:
        report_scale = 1.0
        report_image = Image.open(file_path)
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
    render_report()


def scroll_report(delta_x=0, delta_y=0):
    if report_image is None:
        return

    delta_x = max(-5, min(5, delta_x))
    delta_y = max(-5, min(5, delta_y))

    if delta_x != 0:
        report_canvas.xview_scroll(int(delta_x), "units")
    if delta_y != 0:
        report_canvas.yview_scroll(int(delta_y), "units")


# =============================
# MODULE SWITCHING
# =============================

def switch_module(module_name):
    global current_controller, default_camera

    if default_camera:
        default_camera.release()
        default_camera = None

    if current_controller:
        current_controller.release()

    if module_name == "H.A.N.D.S":
        current_controller = HandsController(
            scroll_callback=scroll_report,
            zoom_callback=zoom_report
        )

    elif module_name == "H.E.A.D":
        current_controller = HeadScrollController(
            zoom_callback=zoom_report,
            scroll_callback=scroll_report
        )

    elif module_name == "I.R.I.S":
        current_controller = IrisController(
            zoom_callback=zoom_report,
            scroll_callback=scroll_report
        )


# =============================
# VIDEO LOOP (MIRRORED)
# =============================

def update_video():
    frame = None

    if current_controller:
        frame = current_controller.get_frame()
    elif default_camera:
        ret, raw = default_camera.read()
        if ret:
            frame = raw

    if frame is not None:
        frame = cv2.resize(frame, (700, 500))

        # 🔁 MIRROR VIDEO HERE
       #frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        imgtk = ImageTk.PhotoImage(img)

        camera_label.imgtk = imgtk
        camera_label.configure(image=imgtk)

    root.after(10, update_video)


# =============================
# SHUTDOWN
# =============================

def shutdown():
    global current_controller, default_camera

    if current_controller:
        current_controller.release()

    if default_camera:
        default_camera.release()

    root.destroy()


animate_boot()
root.mainloop()