import requests
import cv2
import threading
import tkinter as tk

from tkinter import (
    messagebox,
    simpledialog
)

AI_SERVER = "http://localhost:8000"

BACKEND_URL = None

cameras = []
locations = {}
room_map = {}

cam_servers = {}

# =====================
# Backend communication
# =====================

def login(username, password):

    global BACKEND_URL
    global cam_servers

    if username != "account" or password != "123456789":

        messagebox.showerror(
            "Login Failed",
            "Invalid account"
        )

        return False

    try:

        response = requests.get(
            f"{AI_SERVER}/cameras",
            params={
                "account": username
            }
        )

        response.raise_for_status()

        servers = response.json()["servers"]

        if not servers:

            messagebox.showerror(
                "Error",
                "No camera servers available"
            )

            return False

        cam_servers = {}

        for s in servers:

            cam_servers[s["cam_server_id"]] = s

        # use first backend
        BACKEND_URL = servers[0]["url"]

        return True

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )

        return False


def get_cameras():

    global cameras

    try:

        response = requests.get(
            f"{BACKEND_URL}/cameras"
        )

        response.raise_for_status()

        cameras = response.json()["cameras"]

    except Exception as e:

        messagebox.showerror(
            "Error",
            str(e)
        )


def group_by_location():

    global locations

    locations = {}

    for cam in cameras:

        loc = cam["location"]

        if loc not in locations:
            locations[loc] = []

        locations[loc].append(cam)


# =====================
# Camera Stream
# =====================

def stream_camera(url):

    cap = cv2.VideoCapture(url)

    if not cap.isOpened():

        messagebox.showerror(
            "Error",
            "Cannot open stream"
        )

        return

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow(
            "Camera Stream (press q to exit)",
            frame
        )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()

    cv2.destroyAllWindows()


def start_stream():

    room = room_var.get()

    if room == "":
        return

    cam = room_map[room]

    thread = threading.Thread(
        target=stream_camera,
        args=(cam["stream_url"],),
        daemon=True
    )

    thread.start()


# =====================
# Face Register API
# =====================

def register_face_api(
    frame,
    name,
    cam_server_id
):

    _, buffer = cv2.imencode(
        ".jpg",
        frame
    )

    files = {
        "file": (
            "frame.jpg",
            buffer.tobytes(),
            "image/jpeg"
        )
    }

    data = {
        "name": name,
        "cam_server_id": cam_server_id
    }

    response = requests.post(
        f"{AI_SERVER}/register",
        files=files,
        data=data
    )

    response.raise_for_status()

    return response.json()


# =====================
# Register Face
# =====================

def register_face():

    cam_server_id = server_var.get()

    if cam_server_id == "":

        messagebox.showerror(
            "Error",
            "Select camera server first"
        )

        return

    # =====================
    # INPUT NAME
    # =====================

    name = simpledialog.askstring(
        "Register Face",
        "Enter name"
    )

    if name is None or name.strip() == "":
        return

    # =====================
    # OPEN WEBCAM
    # =====================

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():

        messagebox.showerror(
            "Error",
            "Cannot open webcam"
        )

        return

    messagebox.showinfo(
        "Info",
        "Press SPACE to capture face"
    )

    frame = None

    while True:

        ret, img = cap.read()

        if not ret:
            break

        cv2.imshow(
            "Register Face - Press SPACE",
            img
        )

        key = cv2.waitKey(1)

        # SPACE
        if key == 32:

            frame = img.copy()

            break

        # ESC
        if key == 27:

            cap.release()

            cv2.destroyAllWindows()

            return

    cap.release()

    cv2.destroyAllWindows()

    if frame is None:
        return

    # =====================
    # REGISTER API
    # =====================

    try:

        result = register_face_api(
            frame=frame,
            name=name,
            cam_server_id=cam_server_id
        )

        print(result)

        saved_ids = result.get(
            "saved_ids",
            []
        )

        skipped_faces = result.get(
            "skipped_faces",
            []
        )

        message = result.get(
            "message"
        )

        # =====================
        # SUCCESS
        # =====================

        if len(saved_ids) > 0:

            messagebox.showinfo(
                "Success",
                f"Saved IDs:\n{saved_ids}"
            )

        else:

            reason = message

            if skipped_faces:

                reason += (
                    f"\n\nSkipped:\n"
                    f"{skipped_faces}"
                )

            messagebox.showwarning(
                "Skipped",
                reason
            )

    except Exception as e:

        messagebox.showerror(
            "Error",
            f"Register failed\n{e}"
        )


# =====================
# GUI Logic
# =====================

def handle_login():

    username = username_entry.get()

    password = password_entry.get()

    if login(username, password):

        # =====================
        # SERVER DROPDOWN
        # =====================

        server_menu["menu"].delete(
            0,
            "end"
        )

        for sid in cam_servers.keys():

            server_menu["menu"].add_command(
                label=sid,
                command=lambda v=sid:
                server_var.set(v)
            )

        server_var.set(
            list(cam_servers.keys())[0]
        )

        # =====================
        # LOAD CAMERAS
        # =====================

        get_cameras()

        group_by_location()

        # =====================
        # LOCATION DROPDOWN
        # =====================

        location_menu["menu"].delete(
            0,
            "end"
        )

        for loc in locations.keys():

            location_menu["menu"].add_command(
                label=loc,
                command=lambda v=loc:
                location_var.set(v)
            )

        location_var.set(
            list(locations.keys())[0]
        )

        update_rooms()


def update_rooms():

    loc = location_var.get()

    room_menu["menu"].delete(
        0,
        "end"
    )

    global room_map

    room_map = {}

    for cam in locations[loc]:

        name = cam["room"]

        room_map[name] = cam

        room_menu["menu"].add_command(
            label=name,
            command=lambda v=name:
            room_var.set(v)
        )

    room_var.set(
        list(room_map.keys())[0]
    )


# =====================
# Build UI
# =====================

root = tk.Tk()

root.title("SmartHome Camera Demo")

root.geometry("450x400")

root.configure(bg="#1e1e2f")

FONT_TITLE = (
    "Segoe UI",
    16,
    "bold"
)

FONT = (
    "Segoe UI",
    10
)

# =====================
# Main Card
# =====================

main_frame = tk.Frame(
    root,
    bg="#2b2b3c",
    padx=20,
    pady=20
)

main_frame.pack(
    padx=20,
    pady=20,
    fill="both",
    expand=True
)

# =====================
# Title
# =====================

tk.Label(
    main_frame,
    text="SmartHome Camera",
    font=FONT_TITLE,
    fg="white",
    bg="#2b2b3c"
).pack(
    pady=(0, 15)
)

# =====================
# Login Section
# =====================

login_frame = tk.Frame(
    main_frame,
    bg="#2b2b3c"
)

login_frame.pack(
    fill="x",
    pady=5
)

tk.Label(
    login_frame,
    text="Username",
    fg="white",
    bg="#2b2b3c",
    font=FONT
).grid(
    row=0,
    column=0,
    sticky="w"
)

username_entry = tk.Entry(
    login_frame,
    font=FONT,
    bg="#3a3a4f",
    fg="white",
    insertbackground="white"
)

username_entry.grid(
    row=0,
    column=1,
    padx=10,
    pady=5
)

tk.Label(
    login_frame,
    text="Password",
    fg="white",
    bg="#2b2b3c",
    font=FONT
).grid(
    row=1,
    column=0,
    sticky="w"
)

password_entry = tk.Entry(
    login_frame,
    show="*",
    font=FONT,
    bg="#3a3a4f",
    fg="white",
    insertbackground="white"
)

password_entry.grid(
    row=1,
    column=1,
    padx=10,
    pady=5
)

tk.Button(
    login_frame,
    text="Login",
    command=handle_login,
    bg="#4CAF50",
    fg="white",
    activebackground="#45a049",
    relief="flat",
    padx=10,
    pady=5
).grid(
    row=2,
    columnspan=2,
    pady=10
)

# =====================
# Dropdown Section
# =====================

section_frame = tk.Frame(
    main_frame,
    bg="#2b2b3c"
)

section_frame.pack(
    fill="x",
    pady=10
)

# =====================
# Camera Server
# =====================

server_var = tk.StringVar()

tk.Label(
    section_frame,
    text="Camera Server",
    fg="white",
    bg="#2b2b3c",
    font=FONT
).pack(
    anchor="w"
)

server_menu = tk.OptionMenu(
    section_frame,
    server_var,
    ""
)

server_menu.config(
    bg="#3a3a4f",
    fg="white",
    highlightthickness=0
)

server_menu.pack(
    fill="x",
    pady=5
)

# =====================
# Location
# =====================

location_var = tk.StringVar()

tk.Label(
    section_frame,
    text="Location",
    fg="white",
    bg="#2b2b3c",
    font=FONT
).pack(
    anchor="w"
)

location_menu = tk.OptionMenu(
    section_frame,
    location_var,
    ""
)

location_menu.config(
    bg="#3a3a4f",
    fg="white",
    highlightthickness=0
)

location_menu.pack(
    fill="x",
    pady=5
)

location_var.trace_add(
    "write",
    lambda *args: update_rooms()
)

# =====================
# Room
# =====================

room_var = tk.StringVar()

tk.Label(
    section_frame,
    text="Room",
    fg="white",
    bg="#2b2b3c",
    font=FONT
).pack(
    anchor="w"
)

room_menu = tk.OptionMenu(
    section_frame,
    room_var,
    ""
)

room_menu.config(
    bg="#3a3a4f",
    fg="white",
    highlightthickness=0
)

room_menu.pack(
    fill="x",
    pady=5
)

# =====================
# Buttons
# =====================

btn_frame = tk.Frame(
    main_frame,
    bg="#2b2b3c"
)

btn_frame.pack(
    pady=15
)

tk.Button(
    btn_frame,
    text="Open Camera",
    command=start_stream,
    bg="#2196F3",
    fg="white",
    relief="flat",
    padx=15,
    pady=8
).grid(
    row=0,
    column=0,
    padx=10
)

tk.Button(
    btn_frame,
    text="Register Face",
    command=register_face,
    bg="#FF9800",
    fg="white",
    relief="flat",
    padx=15,
    pady=8
).grid(
    row=0,
    column=1,
    padx=10
)

# =====================
# Run App
# =====================

root.mainloop()