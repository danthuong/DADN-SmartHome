import requests
import cv2
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog
import base64
import numpy as np

AI_SERVER = "http://localhost:8000"
BACKEND_URL = None

cameras = []
locations = {}
room_map = {}

cam_servers = {}
selected_cam_server_id = None


# =====================
# Backend communication
# =====================

def login(username, password):

    global BACKEND_URL
    global cam_servers

    if username != "TuanDuy" or password != "12345":
        messagebox.showerror("Login Failed", "Invalid account")
        return False

    try:
        response = requests.get(
            f"{AI_SERVER}/cameras",
            params={"account": username}
        )

        response.raise_for_status()

        servers = response.json()["servers"]

        if not servers:
            messagebox.showerror("Error", "No camera servers available")
            return False

        cam_servers = {}

        for s in servers:
            cam_servers[s["cam_server_id"]] = s

        BACKEND_URL = servers[0]["url"]

        return True

    except Exception as e:
        messagebox.showerror("Error", str(e))
        return False


def get_cameras():

    global cameras

    try:
        response = requests.get(f"{BACKEND_URL}/cameras")
        response.raise_for_status()
        cameras = response.json()["cameras"]
    except Exception as e:
        messagebox.showerror("Error", str(e))


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
        messagebox.showerror("Error", "Cannot open stream")
        return

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow("Camera Stream (press q to exit)", frame)

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

def detect_faces(frame):

    _, buffer = cv2.imencode(".jpg", frame)

    files = {
        "file": ("frame.jpg", buffer.tobytes(), "image/jpeg")
    }

    response = requests.post(
        f"{AI_SERVER}/register/detect",
        files=files
    )

    response.raise_for_status()

    return response.json()["faces"]


def save_faces(face_payload):

    response = requests.post(
        f"{AI_SERVER}/register/save",
        json={"faces": face_payload}
    )

    response.raise_for_status()

    return response.json()


# =====================
# Register Face
# =====================

def register_face():

    cam_server_id = server_var.get()

    if cam_server_id == "":
        messagebox.showerror("Error", "Select camera server first")
        return

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        messagebox.showerror("Error", "Cannot open webcam")
        return

    messagebox.showinfo("Info", "Press SPACE to capture face")

    while True:

        ret, frame = cap.read()

        if not ret:
            break

        cv2.imshow("Register Face - Press SPACE", frame)

        key = cv2.waitKey(1)

        if key == 32:  # SPACE
            break

        if key == 27:  # ESC
            cap.release()
            cv2.destroyAllWindows()
            return

    cap.release()
    cv2.destroyAllWindows()

    try:
        faces = detect_faces(frame)
    except Exception as e:
        messagebox.showerror("Error", f"Detect failed\n{e}")
        return

    if len(faces) == 0:
        messagebox.showinfo("Info", "No faces detected")
        return

    face_payload = []

    for face in faces:

        face_img = base64.b64decode(face["image"])

        nparr = np.frombuffer(face_img, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        cv2.imshow("Detected Face", img)
        cv2.waitKey(1)

        name = simpledialog.askstring(
            "Register Face",
            "Enter name (or type 'skip')"
        )

        if name is None or name.lower() == "skip":
            continue

        face_payload.append({
            "face_id": face["face_id"],
            "name": name,
            "cam_server_id": cam_server_id
        })

        cv2.destroyAllWindows()

    if len(face_payload) == 0:
        messagebox.showinfo("Info", "No faces selected")
        return

    try:
        result = save_faces(face_payload)
        messagebox.showinfo("Success", f"Saved IDs: {result['saved_ids']}")
    except Exception as e:
        messagebox.showerror("Error", f"Save failed\n{e}")


# =====================
# GUI Logic
# =====================

def handle_login():

    username = username_entry.get()
    password = password_entry.get()

    if login(username, password):

        # populate server dropdown
        server_menu["menu"].delete(0, "end")

        for sid in cam_servers.keys():
            server_menu["menu"].add_command(
                label=sid,
                command=lambda v=sid: server_var.set(v)
            )

        server_var.set(list(cam_servers.keys())[0])

        get_cameras()
        group_by_location()

        location_menu["menu"].delete(0, "end")

        for loc in locations.keys():
            location_menu["menu"].add_command(
                label=loc,
                command=lambda v=loc: location_var.set(v)
            )

        location_var.set(list(locations.keys())[0])
        update_rooms()


def update_rooms():

    loc = location_var.get()

    room_menu["menu"].delete(0, "end")

    global room_map
    room_map = {}

    for cam in locations[loc]:

        name = cam["room"]
        room_map[name] = cam

        room_menu["menu"].add_command(
            label=name,
            command=lambda v=name: room_var.set(v)
        )

    room_var.set(list(room_map.keys())[0])


# =====================
# Build UI (Improved)
# =====================

root = tk.Tk()
root.title("SmartHome Camera Demo")
root.geometry("450x400")
root.configure(bg="#1e1e2f")

FONT_TITLE = ("Segoe UI", 16, "bold")
FONT = ("Segoe UI", 10)

# ===== Card Frame =====
main_frame = tk.Frame(root, bg="#2b2b3c", padx=20, pady=20)
main_frame.pack(padx=20, pady=20, fill="both", expand=True)

# ===== Title =====
tk.Label(
    main_frame,
    text="SmartHome Camera",
    font=FONT_TITLE,
    fg="white",
    bg="#2b2b3c"
).pack(pady=(0, 15))

# ===== Login =====
login_frame = tk.Frame(main_frame, bg="#2b2b3c")
login_frame.pack(fill="x", pady=5)

tk.Label(login_frame, text="Username", fg="white", bg="#2b2b3c", font=FONT).grid(row=0, column=0, sticky="w")
username_entry = tk.Entry(login_frame, font=FONT, bg="#3a3a4f", fg="white", insertbackground="white")
username_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(login_frame, text="Password", fg="white", bg="#2b2b3c", font=FONT).grid(row=1, column=0, sticky="w")
password_entry = tk.Entry(login_frame, show="*", font=FONT, bg="#3a3a4f", fg="white", insertbackground="white")
password_entry.grid(row=1, column=1, padx=10, pady=5)

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
).grid(row=2, columnspan=2, pady=10)

# ===== Dropdown Section =====
section_frame = tk.Frame(main_frame, bg="#2b2b3c")
section_frame.pack(fill="x", pady=10)

# Camera Server
server_var = tk.StringVar()
tk.Label(section_frame, text="Camera Server", fg="white", bg="#2b2b3c", font=FONT).pack(anchor="w")
server_menu = tk.OptionMenu(section_frame, server_var, "")
server_menu.config(bg="#3a3a4f", fg="white", highlightthickness=0)
server_menu.pack(fill="x", pady=5)

# Location
location_var = tk.StringVar()
tk.Label(section_frame, text="Location", fg="white", bg="#2b2b3c", font=FONT).pack(anchor="w")
location_menu = tk.OptionMenu(section_frame, location_var, "")
location_menu.config(bg="#3a3a4f", fg="white", highlightthickness=0)
location_menu.pack(fill="x", pady=5)

location_var.trace_add("write", lambda *args: update_rooms())

# Room
room_var = tk.StringVar()
tk.Label(section_frame, text="Room", fg="white", bg="#2b2b3c", font=FONT).pack(anchor="w")
room_menu = tk.OptionMenu(section_frame, room_var, "")
room_menu.config(bg="#3a3a4f", fg="white", highlightthickness=0)
room_menu.pack(fill="x", pady=5)

# ===== Buttons =====
btn_frame = tk.Frame(main_frame, bg="#2b2b3c")
btn_frame.pack(pady=15)

tk.Button(
    btn_frame,
    text="Open Camera",
    command=start_stream,
    bg="#2196F3",
    fg="white",
    relief="flat",
    padx=15,
    pady=8
).grid(row=0, column=0, padx=10)

tk.Button(
    btn_frame,
    text="Register Face",
    command=register_face,
    bg="#FF9800",
    fg="white",
    relief="flat",
    padx=15,
    pady=8
).grid(row=0, column=1, padx=10)

root.mainloop()