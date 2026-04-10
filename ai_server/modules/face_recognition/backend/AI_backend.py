import cv2
import numpy as np
import torch
from fastapi import FastAPI, UploadFile, File, Form

from models.recognition import ModelFactory
from models.anti_sproof import SilentFaceModel

from database.CameraAccountDb import JSONCameraAccountDb
from database.FRDb import (
    Info,
    DbFactory,
)

from ..config.config import (
    Retina_ArcConfig,
    JSONDbConfig,
)

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

# ===============================
# Load database
# ===============================

dbConfig = JSONDbConfig(
    "frdb.json",
    "images"
)

db = DbFactory.create(
    "jsonDb",
    dbConfig
)

camera_account_db = JSONCameraAccountDb(
    "camera_accounts.json"
)

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
import uuid
@app.post("/register/detect")
async def detect_register_faces(
    file: UploadFile = File(...)
):

    frame = await read_frame(file)

    if frame is None:
        return {"faces": []}

    faces = detect_face(model, frame)

    if len(faces) == 0:
        return {"faces": []}

    cropped_faces = crop_face(frame, faces)

    results = []

    for face_img, face in cropped_faces:

        face_id = str(uuid.uuid4())

        temp_faces[face_id] = (face_img, face)

        _, buffer = cv2.imencode(".jpg", face_img)

        face_base64 = base64.b64encode(buffer).decode()

        results.append({
            "face_id": face_id,
            "image": face_base64
        })

    return {
        "faces": results
    }

from pydantic import BaseModel
from typing import Optional, List

class FaceRegister(BaseModel):
    face_id: str
    name: str
    cam_server_id: Optional[str] = None


class RegisterRequest(BaseModel):
    faces: List[FaceRegister]

@app.post("/register/save")
def register_faces(req: RegisterRequest):

    face_list = []

    for f in req.faces:

        if f.face_id not in temp_faces:
            continue

        face_img, face = temp_faces[f.face_id]

        info = Info(
            name=f.name if f.name else None,
            cam_server_id=f.cam_server_id if f.cam_server_id else None
        )

        face_list.append((face_img, face, info))

    if len(face_list) == 0:
        return {"saved_ids": []}

    ids = add_face(db, face_list)
    cam_server_cache.clear()

    return {
        "saved_ids": ids
    }