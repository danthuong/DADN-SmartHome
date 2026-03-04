import cv2
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import threading
import time

app = FastAPI()

# ===============================
# CAMERA INIT
# ===============================

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("Cannot open webcam")

# Lock để tránh race condition
frame_lock = threading.Lock()
output_frame = None


# ===============================
# BACKGROUND CAMERA THREAD
# ===============================

def capture_frames():
    global output_frame
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed")
            break

        with frame_lock:
            output_frame = frame.copy()

        time.sleep(0.01)


threading.Thread(target=capture_frames, daemon=True).start()


# ===============================
# STREAM GENERATOR
# ===============================

def generate():
    global output_frame

    while True:
        with frame_lock:
            if output_frame is None:
                continue
            frame = output_frame.copy()

        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame_bytes +
            b"\r\n"
        )


# ===============================
# API
# ===============================

@app.get("/video")
def video_feed():
    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/")
def root():
    return {"status": "Camera backend running"}