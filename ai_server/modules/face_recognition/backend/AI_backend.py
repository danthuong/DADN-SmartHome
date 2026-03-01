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

from utils.similarity_compute import CosineSimilarity

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
        location_cache[location] = knowFaces
    return location_cache[location]

import numpy as np
from collections import defaultdict

def preprocessing(knowFaces):
    grouped = defaultdict(list)

    # Normalize từng embedding và gom nhóm
    for emb, name in knowFaces:
        emb = np.array(emb)
        norm = np.linalg.norm(emb)
        if norm > 0:
            emb = emb / norm
        grouped[name].append(emb)

    processed_faces = []

    # Tính centroid cho từng người
    for name, emb_list in grouped.items():
        centroid = np.mean(emb_list, axis=0)

        # Normalize lại centroid
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        processed_faces.append((centroid, name))

    return processed_faces

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
    knowFaces = preprocessing(knowFaces)

    # detect
    faces = model.detect(frame)

    results = []

    for face in faces:
        x1, y1, x2, y2 = face.bbox.astype(int)

        # clamp
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        embedding = face.embedding

        # -------------------------
        # Recognition
        # -------------------------
        best_name = "Unknown"
        best_score = 0.0

        for known_emb, known_name in knowFaces:
            sim = similarity.compute(embedding, known_emb)
            print("Similarity:", sim)
            if sim > 0.75 and sim > best_score:
                best_score = sim
                best_name = known_name

        results.append({
            "bbox": [int(x1), int(y1), int(x2), int(y2)],
            "embedding": embedding.tolist(),
            "name": best_name,
            "score": float(best_score)
        })

    return results