import cv2
import numpy as np
import base64
from fastapi import FastAPI
from pydantic import BaseModel
from models.model import ModelFactory
from database.FRDb import (
    Info,
    DbFactory, 
)
from ..config.config import (
    Retina_ArcConfig, 
    JSONDbConfig,
    )

from ..utils.similarity_compute import CosineSimilarity

# ===============================
# Init FastAPI
# ===============================
app = FastAPI()

# ===============================
# Load model (1 lần duy nhất)
# ===============================

modelConfig = Retina_ArcConfig(
    device="cpu",
    det_size=640,
    scale="s"
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

similarity = CosineSimilarity()

# cache embeddings theo location
location_cache = {}

# ===============================
# Request schema
# ===============================
class DetectRequest(BaseModel):
    frame: str
    location: str


# ===============================
# Utils
# ===============================
def decode_frame(frame_base64):
    img_bytes = base64.b64decode(frame_base64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return frame


def load_known_faces(location):
    if location not in location_cache:
        print(f"Loading embeddings for location: {location}")
        knowFaces = db.getEmbedding(Info(location=location))
        knowFaces = preprocessing(knowFaces)
        location_cache[location] = knowFaces
    return location_cache[location]

import numpy as np
from collections import defaultdict

def preprocessing(knowFaces):
    grouped = defaultdict(list)

    # Normalize từng embedding và gom nhóm
    for emb, name in knowFaces:
        emb = np.array(emb, dtype=np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        grouped[name].append(emb)

    embeddings = []
    names = []

    # Tính centroid cho từng người
    for name, emb_list in grouped.items():
        centroid = np.mean(emb_list, axis=0)

        # Normalize lại centroid
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        embeddings.append(centroid)
        names.append(name)

    if len(embeddings) == 0:
        return {
            "embeddings": np.empty((0, 512), dtype=np.float32),
            "names": []
        }

    return {
        "embeddings": np.stack(embeddings),  # (N, 512)
        "names": names
    }

# ===============================
# Detect endpoint
# ===============================
@app.post("/detect")
def detect(req: DetectRequest):

    frame = decode_frame(req.frame)
    location = req.location

    if frame is None:
        return []

    # load đúng DB theo location
    knowFaces = load_known_faces(location)

    # detect
    faces = model.detect(frame)

    results = []

    # ===== Detect xong =====
    faces = model.detect(frame)

    results = []

    if len(faces) == 0:
        return results

    db_embeddings = knowFaces["embeddings"]      # (N, 512)
    db_names = knowFaces["names"]

    # -------------------------
    # Build face embedding matrix (M, 512)
    # -------------------------
    face_embeddings = []
    bboxes = []

    h, w = frame.shape[:2]

    for face in faces:
        x1, y1, x2, y2 = face.bbox.astype(int)

        # clamp
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        emb = face.embedding.astype(np.float32)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm

        face_embeddings.append(emb)
        bboxes.append((x1, y1, x2, y2))

    if len(face_embeddings) == 0:
        return results

    face_embeddings = np.stack(face_embeddings)   # (M, 512)

    # -------------------------
    # Tensor similarity
    # (M, 512) @ (512, N) = (M, N)
    # -------------------------
    sims = similarity.compute(face_embeddings, db_embeddings)

    # -------------------------
    # Find best match for each face
    # -------------------------
    for i in range(face_embeddings.shape[0]):

        x1, y1, x2, y2 = bboxes[i]

        best_name = "Unknown"
        best_score = 0.0

        if sims.shape[1] > 0:
            best_idx = np.argmax(sims[i])
            best_score = sims[i][best_idx]

            if best_score > 0.6:
                best_name = db_names[best_idx]

        results.append({
        "bbox": [int(x1), int(y1), int(x2), int(y2)],
        "embedding": face_embeddings[i].tolist(),
        "name": best_name,
        "score": float(best_score)
    })

    return results