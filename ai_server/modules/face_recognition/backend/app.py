import requests
import cv2
import threading
import tkinter as tk
import websocket
import json
import time

from tkinter import messagebox, simpledialog

AI_SERVER = "http://localhost:8000"

BACKEND_URL = None
cameras = []
locations = {}
room_map = {}
cam_servers = {}

# =====================
# LOGIN
# =====================

def login(username, password):

    global BACKEND_URL, cam_servers

    if username != "account" or password != "123456789":
        messagebox.showerror("Login Failed", "Invalid account")
        return False

    try:
        response = requests.get(
            f"{AI_SERVER}/cameras",
            params={"account": username}
        )

        response.raise_for_status()

        servers = response.json()["servers"]

        cam_servers = {s["cam_server_id"]: s for s in servers}
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
        locations.setdefault(loc, []).append(cam)


# =====================
# STREAM CAMERA
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

    threading.Thread(
        target=stream_camera,
        args=(cam["stream_url"],),
        daemon=True
    ).start()


# =====================
# WEBSOCKET REGISTER (AUTO LOOP)
# =====================

def register_face_ws(frame, name, cam_server_id):

    ws = websocket.create_connection(
        f"{AI_SERVER.replace('http', 'ws')}/ws/register"
    )

    try:

        while True:

            ok, buffer = cv2.imencode(".jpg", frame)
            if not ok:
                continue

            payload = {
                "file": list(buffer.tobytes()),
                "name": name,
                "cam_server_id": cam_server_id
            }

            ws.send(json.dumps(payload))
            result = json.loads(ws.recv())

            msg = result.get("message", "")
            print("WS:", msg)

            if msg == "success":
                ws.close()
                return result

            time.sleep(0.2)

    except Exception as e:
        ws.close()
        raise e


# =====================
# REGISTER FACE
# =====================

def register_face():

    cam_server_id = server_var.get()

    if cam_server_id == "":
        messagebox.showerror("Error", "Select camera server first")
        return

    name = simpledialog.askstring("Register Face", "Enter name")

    if not name:
        return

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        messagebox.showerror("Error", "Cannot open webcam")
        return

    messagebox.showinfo(
        "Info",
        "Auto registering until SUCCESS..."
    )

    try:

        while True:

            ret, frame = cap.read()
            if not ret:
                break

            cv2.imshow("Register Face (AUTO WS)", frame)

            result = register_face_ws(frame, name, cam_server_id)

            if result and result.get("message") == "success":

                messagebox.showinfo(
                    "Success",
                    "Register face successful"
                )
                break

            if cv2.waitKey(1) & 0xFF == 27:
                break

    except Exception as e:
        messagebox.showerror("Error", str(e))

    cap.release()
    cv2.destroyAllWindows()


# =====================
# LOGIN HANDLER
# =====================

def handle_login():

    username = username_entry.get()
    password = password_entry.get()

    if login(username, password):

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
# UI (FIXED LOGIN UI FULL)
# =====================

root = tk.Tk()
root.title("SmartHome Camera Demo")
root.geometry("450x500")
root.configure(bg="#1e1e2f")

FONT_TITLE = ("Segoe UI", 16, "bold")

main_frame = tk.Frame(root, bg="#2b2b3c", padx=20, pady=20)
main_frame.pack(fill="both", expand=True)

tk.Label(
    main_frame,
    text="SmartHome Camera",
    font=FONT_TITLE,
    fg="white",
    bg="#2b2b3c"
).pack(pady=10)

# =====================
# LOGIN UI (RESTORED)
# =====================

login_frame = tk.Frame(main_frame, bg="#2b2b3c")
login_frame.pack(fill="x", pady=10)

tk.Label(login_frame, text="Username", fg="white", bg="#2b2b3c").grid(row=0, column=0, sticky="w")

username_entry = tk.Entry(login_frame)
username_entry.grid(row=0, column=1, padx=10, pady=5)

tk.Label(login_frame, text="Password", fg="white", bg="#2b2b3c").grid(row=1, column=0, sticky="w")

password_entry = tk.Entry(login_frame, show="*")
password_entry.grid(row=1, column=1, padx=10, pady=5)

tk.Button(
    login_frame,
    text="Login",
    command=handle_login,
    bg="#4CAF50",
    fg="white"
).grid(row=2, columnspan=2, pady=10)

# =====================
# DROPDOWNS
# =====================

server_var = tk.StringVar()
location_var = tk.StringVar()
room_var = tk.StringVar()

server_menu = tk.OptionMenu(main_frame, server_var, "")
location_menu = tk.OptionMenu(main_frame, location_var, "")
room_menu = tk.OptionMenu(main_frame, room_var, "")

server_menu.pack(fill="x", pady=5)
location_menu.pack(fill="x", pady=5)
room_menu.pack(fill="x", pady=5)

# =====================
# BUTTONS
# =====================

tk.Button(
    main_frame,
    text="Open Camera",
    command=start_stream,
    bg="#2196F3"
).pack(pady=10)

tk.Button(
    main_frame,
    text="Register Face (AUTO WS)",
    command=register_face,
    bg="#FF9800"
).pack()

root.mainloop()