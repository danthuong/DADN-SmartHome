import cv2
import numpy as np
import torch
from fastapi import FastAPI, UploadFile, File, Form
from models.face_quality import MediaPipe_Heuristic
from models.recognition import ModelFactory
from models.anti_sproof import SilentFaceModel

from database.CameraAccountDb import SQLiteCameraAccountDb
from database.FRDb import (
    Info,
    HybridFaceDB,
)

from ..config.config import (
    Retina_ArcConfig,
    HybridConfig,
)
import os
from dotenv import load_dotenv

from collections import defaultdict
from PIL import Image

# ===============================
# Device
# ===============================

device = torch.device(
    "cuda" if torch.cuda.is_available() else "cpu"
)

# ===============================
# Init FastAPI
# ===============================

app = FastAPI()

# ===============================
# Load Face Recognition model
# ===============================

modelConfig = Retina_ArcConfig(
    device=str(device),
    det_size=640,
    scale="l"
)

model = ModelFactory.create(
    "retina_arc",
    modelConfig
)

# ===============================
# Load Anti-Spoof model
# ===============================

anti_spoof_config = {
    "model_dir":
    "modules/face_recognition/"
    "Silent_Face_Anti_Spoofing/"
    "resources/anti_spoof_models",

    "device_id": 0
}

print("Loading Anti-Spoof model...")

anti_spoof_model = SilentFaceModel(
    anti_spoof_config
)

face_quality_model = MediaPipe_Heuristic()

# ===============================
# Load database
# ===============================

dbConfig = HybridConfig()
db = HybridFaceDB(dbConfig)

camera_account_db = SQLiteCameraAccountDb()

# ===============================
# Cache
# ===============================

cam_server_cache = {}
temp_faces = {}
# ===============================
# Utils
# ===============================

async def read_frame(file: UploadFile):

    contents = await file.read()

    np_arr = np.frombuffer(
        contents,
        np.uint8
    )

    frame = cv2.imdecode(
        np_arr,
        cv2.IMREAD_COLOR
    )

    return frame


def load_known_faces(cam_server_id):

    if cam_server_id not in cam_server_cache:

        print(
            f"Loading embeddings for cam_server_id: {cam_server_id}"
        )

        knowFaces = db.getEmbedding(
            Info(cam_server_id=cam_server_id)
        )

        knowFaces = preprocessing(
            knowFaces,
            device
        )

        cam_server_cache[cam_server_id] = knowFaces

    return cam_server_cache[cam_server_id]


def preprocessing(knowFaces, device):

    grouped = defaultdict(list)

    for emb, name in knowFaces:

        emb = torch.tensor(
            emb,
            dtype=torch.float32,
            device=device
        )

        norm = torch.norm(emb)

        if norm > 0:
            emb = emb / norm

        grouped[name].append(emb)

    embeddings = []
    names = []

    for name, emb_list in grouped.items():

        stack = torch.stack(emb_list)

        centroid = torch.mean(
            stack,
            dim=0
        )

        norm = torch.norm(centroid)

        if norm > 0:
            centroid = centroid / norm

        embeddings.append(centroid)
        names.append(name)

    if len(embeddings) == 0:

        return {
            "embeddings":
            torch.empty(
                (0, 512),
                dtype=torch.float32,
                device=device
            ),
            "names": []
        }

    embeddings = torch.stack(embeddings)

    return {
        "embeddings": embeddings,
        "names": names
    }


# ===============================
# Anti Spoof check (FIXED)
# ===============================

def check_spoof(frame, bbox):

    x1, y1, x2, y2 = bbox

    h, w = frame.shape[:2]

    # ⭐ ADD MARGIN (RẤT QUAN TRỌNG)
    margin = 0.3

    bw = x2 - x1
    bh = y2 - y1

    x1 = int(x1 - bw * margin)
    y1 = int(y1 - bh * margin)
    x2 = int(x2 + bw * margin)
    y2 = int(y2 + bh * margin)

    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)

    face_img = frame[y1:y2, x1:x2]

    if face_img.size == 0:
        return "fake"

    print("Face size:", face_img.shape)

    # ⭐ RESIZE CHUẨN SILENTFACE
    face_img = cv2.resize(
        face_img,
        (80, 80)
    )

    face_img = cv2.cvtColor(
        face_img,
        cv2.COLOR_BGR2RGB
    )

    pil_img = Image.fromarray(
        face_img
    )

    try:

        result = anti_spoof_model.sproof_detect(
            pil_img
        )

        print("Spoof result:", result)

        return result

    except Exception as e:

        print("Spoof error:", e)

        return "fake"


# ===============================
# Detect endpoint
# ===============================

@app.post("/detect")
async def detect(
    file: UploadFile = File(...),
    cam_server_id: str = Form(...)
):

    frame = await read_frame(file)

    if frame is None:
        return []

    knowFaces = load_known_faces(
        cam_server_id
    )

    faces = model.detect(frame)

    results = []

    if len(faces) == 0:
        return results

    db_embeddings = knowFaces["embeddings"]
    db_names = knowFaces["names"]

    h, w = frame.shape[:2]

    for face in faces:

        x1, y1, x2, y2 = map(int, face.bbox)

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        # =========================
        # Anti Spoof
        # =========================

        spoof_result = check_spoof(
            frame,
            (x1, y1, x2, y2)
        )

        if spoof_result == "fake":
            print("Fake face detected → skipped")
            continue

        # =========================
        # Recognition
        # =========================

        emb = torch.tensor(
            face.embedding,
            dtype=torch.float32,
            device=device
        )

        norm = torch.norm(emb)

        if norm > 0:
            emb = emb / norm

        if db_embeddings.shape[0] > 0:

            sims = torch.matmul(
                emb.unsqueeze(0),
                db_embeddings.T
            )

            best_score, best_idx = torch.max(
                sims,
                dim=1
            )

            best_score = best_score.item()
            best_idx = best_idx.item()

            best_name = "Unknown"

            if best_score > 0.6:
                best_name = db_names[best_idx]

        else:

            best_name = "Unknown"
            best_score = 0.0

        results.append({
            "bbox": [
                int(x1),
                int(y1),
                int(x2),
                int(y2)
            ],
            "name": str(best_name),
            "score": float(best_score),
            "spoof": "real",

            "embedding":
                emb.cpu().numpy().tolist()
        })

    return results


# ===============================
# Camera endpoint
# ===============================

@app.get("/cameras")
def get_cameras(account: str):

    servers = camera_account_db.get_servers(
        account
    )

    return {
        "account": account,
        "servers": servers
    }

from ..utils.utils import detect_face, crop_face, add_face
import base64
from fastapi import UploadFile, File, Form
import uuid
import cv2
# ===============================
# QUALITY MODEL
# ===============================

def score_face_quality(frame, bbox, save_debug=True, frame_id=None):

    x1, y1, x2, y2 = bbox
    h, w = frame.shape[:2]

    # =========================
    # ADD MARGIN (FOR QUALITY ONLY)
    # =========================
    margin = 0.3

    bw = x2 - x1
    bh = y2 - y1

    mx1 = int(x1 - bw * margin)
    my1 = int(y1 - bh * margin)
    mx2 = int(x2 + bw * margin)
    my2 = int(y2 + bh * margin)

    mx1 = max(0, mx1)
    my1 = max(0, my1)
    mx2 = min(w, mx2)
    my2 = min(h, my2)

    # =========================
    # ORIGINAL FACE (NO MARGIN)
    # =========================
    face_img = frame[y1:y2, x1:x2]

    if face_img.size == 0:
        print("[QUALITY] face size = 0")
        return {
            "quality": 0.0,
            "face_img": None
        }

    # =========================
    # QUALITY FACE (WITH MARGIN)
    # =========================
    quality_face = frame[my1:my2, mx1:mx2]

    if quality_face.size == 0:
        print("[QUALITY] quality face size = 0")
        return {
            "quality": 0.0,
            "face_img": face_img
        }

    # =========================
    # PREPROCESS
    # =========================
    quality_face = cv2.resize(quality_face, (80, 80))
    quality_face = cv2.cvtColor(quality_face, cv2.COLOR_BGR2RGB)

    pil_img = Image.fromarray(quality_face)

    # =========================
    # SCORE
    # =========================
    try:
        quality_score = face_quality_model.face_score(
            pil_img,
            pil_img
        )
        quality_score = float(quality_score)

    except Exception as e:
        print("Quality error:", e)
        return {
            "quality": 0.0,
            "face_img": face_img
        }

    # =========================
    # DEBUG
    # =========================
    if save_debug:
        os.makedirs("./test", exist_ok=True)

        tag = frame_id if frame_id is not None else "na"
        filename = f"frame_{tag}_score_{quality_score:.3f}.jpg"
        save_path = os.path.join("./test", filename)

        cv2.imwrite(save_path, face_img)

    return {
        "quality": quality_score,
        "face_img": face_img
    }


# ===============================
# REGISTER API
# ===============================

from fastapi import WebSocket
import cv2
import numpy as np

@app.websocket("/ws/register")
async def register_ws(websocket: WebSocket):

    await websocket.accept()

    try:
        while True:

            data = await websocket.receive_json()

            # =====================
            # DECODE INPUT
            # =====================
            frame_bytes = data["file"]
            name = data["name"]
            cam_server_id = data["cam_server_id"]

            np_arr = np.frombuffer(bytearray(frame_bytes), np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                await websocket.send_json({
                    "message": "invalid_frame"
                })
                continue

            QUALITY_THRESHOLD = 0.5

            faces = detect_face(model, frame)

            if len(faces) == 0:
                await websocket.send_json({
                    "message": "no_face_detected"
                })
                continue

            face_list = []

            h, w = frame.shape[:2]

            for idx, face in enumerate(faces):

                x1, y1, x2, y2 = map(int, face.bbox)

                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)

                bbox = (x1, y1, x2, y2)

                result = score_face_quality(
                    frame=frame,
                    bbox=bbox,
                    frame_id=idx,
                    save_debug=False,
                )

                quality = result.get("quality", 0.0)
                face_img = result.get("face_img", None)

                print("QUALITY RESULT:", quality)

                if face_img is not None and quality >= QUALITY_THRESHOLD:

                    info = Info(
                        name=name,
                        cam_server_id=cam_server_id
                    )

                    face_list.append((face_img, face, info))

            # =====================
            # RULES (GIỮ NGUYÊN 100%)
            # =====================

            if len(face_list) == 0:
                await websocket.send_json({
                    "message": "no_valid_face"
                })
                continue

            if len(face_list) > 1:
                await websocket.send_json({
                    "message": "more_than_one"
                })
                continue

            ids = add_face(db, face_list)
            cam_server_cache.clear()

            await websocket.send_json({
                "message": "success",
                "ids": ids
            })

    except Exception as e:
        print("WS ERROR:", e)
        await websocket.close()