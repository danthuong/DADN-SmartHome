import cv2
import requests
# import base64
import numpy as np
import threading
import uuid
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from deep_sort_realtime.deepsort_tracker import DeepSort

AI_URL = "http://localhost:8000/detect"

import os
LOCATION = os.getenv("LOCATION")
app = FastAPI()

camera_workers = {}
output_frames = {}
frame_locks = {}


# ==============================
# Models
# ==============================

class RegisterRequest(BaseModel):
    camera_url: str
    room: str


# ==============================
# Utils
# ==============================

# def encode_frame(frame):
#     _, buffer = cv2.imencode(".jpg", frame)
#     return base64.b64encode(buffer).decode("utf-8")

# ==============================
# Camera Worker
# ==============================
DISPLAY_LOCAL = True   # bật/tắt hiển thị màn hình local

import threading
import time
from queue import Queue, Empty

def camera_worker(camera_id, camera_url, location, room):

    session = requests.Session()
    print(f"[INFO] Starting camera {camera_id}")

    frame_queue = Queue(maxsize=1)
    detect_queue = Queue(maxsize=5)

    stop_event = threading.Event()

    latest_detections = []
    detections_lock = threading.Lock()

    # ===============================
    # THREAD 1: CAPTURE
    # ===============================
    def capture_loop():

        cap = cv2.VideoCapture(camera_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        frame_count = 0
        last_detect = 0
        
        while not stop_event.is_set():

            ret, frame = cap.read()
            if not ret:
                print(f"[ERROR] Camera {camera_id} disconnected")
                stop_event.set()
                break

            frame = cv2.resize(frame, (640,640))

            # push frame for tracking
            if frame_queue.full():
                try:
                    frame_queue.get_nowait()
                except:
                    pass

            try:
                frame_queue.put_nowait(frame)
            except:
                pass

            # gửi detect mỗi 10 frame
            if time.time() - last_detect > 0.3:
                last_detect = time.time()
                if detect_queue.full():
                    try:
                        detect_queue.get_nowait()
                    except:
                        pass

                try:
                    detect_queue.put_nowait(frame.copy())
                except:
                    pass

        cap.release()

    # ===============================
    # THREAD 2: DETECT
    # ===============================
    def detect_loop():

        nonlocal latest_detections

        while not stop_event.is_set():

            try:
                frame = detect_queue.get(timeout=1)
            except Empty:
                continue

            _, buffer = cv2.imencode(".jpg", frame)

            try:
                response = session.post(
                    AI_URL,
                    files={"file": buffer.tobytes()},
                    data={"location": location},
                    timeout=10
                )

                if response.status_code == 200:
                    detections = response.json()
                else:
                    detections = []

            except Exception as e:
                print("AI error:", e)
                detections = []

            with detections_lock:
                latest_detections = detections

    # ===============================
    # THREAD 3: TRACKING
    # ===============================
    def tracking_loop():

        tracker = DeepSort(
            max_age=15,
            n_init=3,
            max_cosine_distance=0.4,
            embedder=None
        )

        last_detection_time = 0
        DETECT_INTERVAL = 0.3  # seconds

        while not stop_event.is_set():

            try:
                frame = frame_queue.get(timeout=1)
            except Empty:
                continue

            # lấy detection mới nhất
            with detections_lock:
                detections = list(latest_detections)

            ds_inputs = []
            embeddings = []

            if detections:

                for det in detections:

                    x1, y1, x2, y2 = det["bbox"]
                    embedding = np.array(det["embedding"], dtype=np.float32)
                    name = det["name"]

                    w = x2 - x1
                    h = y2 - y1

                    ds_inputs.append(([x1, y1, w, h], 1.0, name))
                    embeddings.append(embedding)

                tracks = tracker.update_tracks(ds_inputs, embeds=embeddings)

            else:
                # không có detection -> chỉ predict
                tracks = tracker.update_tracks([], embeds=[])

            # ======================
            # DRAW TRACKS
            # ======================

            for track in tracks:

                if not track.is_confirmed():
                    continue

                l, t, r, b = track.to_ltrb()
                track_id = track.track_id
                display_name = track.get_det_class() or "Unknown"

                cv2.rectangle(frame,
                            (int(l), int(t)),
                            (int(r), int(b)),
                            (0, 255, 0),
                            2)

                cv2.putText(
                    frame,
                    f"{display_name} | ID {track_id}",
                    (int(l), int(t) - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

            if DISPLAY_LOCAL:
                cv2.imshow(f"CAM - {location}/{room}", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    stop_event.set()
                    break

            with frame_locks[camera_id]:
                output_frames[camera_id] = frame.copy()

        if DISPLAY_LOCAL:
            cv2.destroyAllWindows()

    # ===============================
    # START THREADS
    # ===============================

    t1 = threading.Thread(target=capture_loop, daemon=True)
    t2 = threading.Thread(target=detect_loop, daemon=True)
    t3 = threading.Thread(target=tracking_loop, daemon=True)

    t1.start()
    t2.start()
    t3.start()

    t1.join()
    t2.join()
    t3.join()


# ==============================
# STREAM
# ==============================

def generate(camera_id):
    while True:
        with frame_locks[camera_id]:
            frame = output_frames.get(camera_id)

        if frame is None:
            time.sleep(0.01)
            continue

        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame_bytes +
            b"\r\n"
        )
        time.sleep(0.03)


@app.get("/video/{camera_id}")
def video_feed(camera_id: str):
    return StreamingResponse(
        generate(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ==============================
# REGISTER
# ==============================
from fastapi import HTTPException
@app.post("/register")
def register_camera(req: RegisterRequest):

    camera_id = str(uuid.uuid4())

    frame_locks[camera_id] = threading.Lock()
    output_frames[camera_id] = None

    thread = threading.Thread(
        target=camera_worker,
        args=(camera_id, req.camera_url, LOCATION, req.room),
        daemon=True
    )

    thread.start()
    camera_workers[camera_id] = thread

    return {
        "status": "registered",
        "camera_id": camera_id,
        "video_url": f"http://127.0.0.1:9000/video/{camera_id}"
    }