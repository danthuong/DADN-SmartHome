import cv2
import requests
import base64
import numpy as np
import threading
import uuid
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from deep_sort_realtime.deepsort_tracker import DeepSort

AI_URL = "http://127.0.0.1:8000/detect"

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
    location: str


# ==============================
# Utils
# ==============================

def encode_frame(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    return base64.b64encode(buffer).decode("utf-8")


def iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    if boxAArea + boxBArea - interArea == 0:
        return 0

    return interArea / float(boxAArea + boxBArea - interArea)


# ==============================
# Camera Worker
# ==============================
DISPLAY_LOCAL = True   # bật/tắt hiển thị màn hình local

import threading
from queue import Queue
from queue import Empty
def camera_worker(camera_id, camera_url, location):

    print(f"[INFO] Starting camera {camera_id}")

    detect_queue = Queue(maxsize=2)

    stop_event = threading.Event()

    # ===============================
    # THREAD 1: CAPTURE + DETECT
    # ===============================
    def detect_loop():

        cap = cv2.VideoCapture(camera_url)
        frame_count = 0

        while not stop_event.is_set():

            ret, frame = cap.read()
            if not ret:
                print(f"[ERROR] Camera {camera_id} disconnected")
                stop_event.set()
                break

            frame_count += 1
            if frame_count % 5 != 0:
                continue
            frame_count = 0

            frame = cv2.resize(frame, (640, 480))
            img_base64 = encode_frame(frame)

            try:
                response = requests.post(
                    AI_URL,
                    json={
                        "frame": img_base64,
                        "location": location
                    },
                    timeout=5
                )
                detections = response.json()
            except Exception as e:
                print("AI error:", e)
                detections = []

            if not detect_queue.full():
                detect_queue.put((frame, detections))

        cap.release()

    # ===============================
    # THREAD 2: TRACKING
    # ===============================
    def tracking_loop():

        tracker = DeepSort(
            max_age=8,
            n_init=3,
            max_cosine_distance=0.4,
            embedder=None
        )

        while not stop_event.is_set():

            try:
                frame, detections = detect_queue.get(timeout=1)
            except Empty:
                continue

            ds_inputs = []
            embeddings = []

            for det in detections:
                x1, y1, x2, y2 = det["bbox"]
                embedding = np.array(det["embedding"], dtype=np.float32)
                name = det["name"]

                w = x2 - x1
                h = y2 - y1

                ds_inputs.append(([x1, y1, w, h], 1.0, name))
                embeddings.append(embedding)

            tracks = tracker.update_tracks(ds_inputs, embeds=embeddings)

            for track in tracks:
                if not track.is_confirmed():
                    continue

                l, t, r, b = track.to_ltrb()
                track_id = track.track_id
                display_name = track.get_det_class() or "Unknown"

                cv2.rectangle(frame, (int(l), int(t)), (int(r), int(b)), (0,255,0), 2)
                cv2.putText(
                    frame,
                    f"{display_name} | ID {track_id}",
                    (int(l), int(t)-10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0,255,0),
                    2
                )

            if DISPLAY_LOCAL:
                cv2.imshow(f"CAM - {location}", frame)
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
    t1 = threading.Thread(target=detect_loop, daemon=True)
    t2 = threading.Thread(target=tracking_loop, daemon=True)

    t1.start()
    t2.start()

    t1.join()
    t2.join()


# ==============================
# STREAM
# ==============================

def generate(camera_id):
    while True:
        with frame_locks[camera_id]:
            frame = output_frames.get(camera_id)

        if frame is None:
            continue

        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame_bytes +
            b"\r\n"
        )


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

    # Kiểm tra location có đúng backend này không
    if req.location != LOCATION:
        raise HTTPException(
            status_code=403,
            detail="Location mismatch. Cannot register camera."
        )

    camera_id = str(uuid.uuid4())

    frame_locks[camera_id] = threading.Lock()
    output_frames[camera_id] = None

    thread = threading.Thread(
        target=camera_worker,
        args=(camera_id, req.camera_url, LOCATION),
        daemon=True
    )

    thread.start()
    camera_workers[camera_id] = thread

    return {
        "status": "registered",
        "camera_id": camera_id,
        "video_url": f"http://127.0.0.1:9000/video/{camera_id}"
    }