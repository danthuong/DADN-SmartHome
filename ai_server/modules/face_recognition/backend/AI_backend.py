import cv2
import numpy as np
import torch
from fastapi import FastAPI, UploadFile, File, Form
from models.model import ModelFactory
from database.CameraAccountDb import JSONCameraAccountDb
from database.FRDb import (
    Info,
    DbFactory,
)

from ..config.config import (
    Retina_ArcConfig,
    JSONDbConfig,
)

from ..utils.similarity_compute import CosineSimilarity

from collections import defaultdict


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ===============================
# Init FastAPI
# ===============================
app = FastAPI()

# ===============================
# Load model (1 lần duy nhất)
# ===============================

modelConfig = Retina_ArcConfig(
    device=str(device),
    det_size=640,
    scale="l"
)

model = ModelFactory.create("retina_arc", modelConfig)

# ===============================
# Load database (1 lần duy nhất)
# ===============================

dbConfig = JSONDbConfig(
    "frdb.json",
    "images"
)
db = DbFactory.create("jsonDb", dbConfig)

camera_account_db = JSONCameraAccountDb("camera_accounts.json")


similarity = CosineSimilarity()

# cache embeddings theo location
cam_server_cache = {}
temp_faces = {}
# ===============================
# Utils
# ===============================

async def read_frame(file: UploadFile):
    contents = await file.read()
    np_arr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame


def load_known_faces(cam_server_id):

    if cam_server_id not in cam_server_cache:

        print(f"Loading embeddings for cam_server_id: {cam_server_id}")

        knowFaces = db.getEmbedding(
            Info(cam_server_id=cam_server_id)
        )

        knowFaces = preprocessing(knowFaces, device)

        cam_server_cache[cam_server_id] = knowFaces

    return cam_server_cache[cam_server_id]


def preprocessing(knowFaces, device):

    grouped = defaultdict(list)

    for emb, name in knowFaces:

        emb = torch.tensor(emb, dtype=torch.float32, device=device)

        norm = torch.norm(emb)
        if norm > 0:
            emb = emb / norm

        grouped[name].append(emb)

    embeddings = []
    names = []

    for name, emb_list in grouped.items():

        stack = torch.stack(emb_list)  # (k,512)

        centroid = torch.mean(stack, dim=0)

        norm = torch.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        embeddings.append(centroid)
        names.append(name)

    if len(embeddings) == 0:
        return {
            "embeddings": torch.empty((0, 512), dtype=torch.float32, device=device),
            "names": []
        }

    embeddings = torch.stack(embeddings)

    return {
        "embeddings": embeddings,
        "names": names
    }


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

    knowFaces = load_known_faces(cam_server_id)

    faces = model.detect(frame)

    results = []

    if len(faces) == 0:
        return results

    db_embeddings = knowFaces["embeddings"]
    db_names = knowFaces["names"]

    face_embeddings = []
    bboxes = []

    h, w = frame.shape[:2]

    for face in faces:

        x1, y1, x2, y2 = face.bbox.astype(int)

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        emb = torch.tensor(face.embedding, dtype=torch.float32, device=device)

        norm = torch.norm(emb)
        if norm > 0:
            emb = emb / norm

        face_embeddings.append(emb)
        bboxes.append((x1, y1, x2, y2))

    if len(face_embeddings) == 0:
        return results

    face_embeddings = torch.stack(face_embeddings)

    # cosine similarity (dot product)
    sims = torch.matmul(face_embeddings, db_embeddings.T)

    best_scores, best_idxs = torch.max(sims, dim=1)

    for i in range(face_embeddings.shape[0]):

        x1, y1, x2, y2 = bboxes[i]

        best_score = best_scores[i].item()
        best_idx = best_idxs[i].item()

        best_name = "Unknown"

        if best_score > 0.6 and sims.shape[1] > 0:
            best_name = db_names[best_idx]

        results.append({
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "embedding": face_embeddings[i].cpu().tolist(),
            "name": best_name,
            "score": float(best_score)
        })

    return results

@app.get("/cameras")
def get_cameras(account: str):

    servers = camera_account_db.get_servers(account)

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