import os
import uuid
import sqlite3
import numpy as np
import cv2

from abc import ABC, abstractmethod
from pinecone import Pinecone
from dotenv import load_dotenv

from modules.face_recognition.config.config import HybridConfig


# ==========================================
# LOAD ENV
# ==========================================

load_dotenv()


# ==========================================
# INFO
# ==========================================

class Info:
    def __init__(self, name=None, cam_server_id=None):
        self.name = name
        self.cam_server_id = cam_server_id


# ==========================================
# BASE DATABASE
# ==========================================

class FRDb(ABC):

    @abstractmethod
    def getEmbedding(self, info: Info):
        pass

    @abstractmethod
    def updateEmbedding(self, info: Info, embedding, img):
        pass


# ==========================================
# SQLITE DATABASE
# ==========================================

class SQLiteFaceDB:

    def __init__(self, db_path):

        self.conn = sqlite3.connect(
            db_path,
            check_same_thread=False
        )

        self.cursor = self.conn.cursor()

    # ======================================
    # INSERT FACE
    # ======================================

    def insert_face(
        self,
        face_id,
        name,
        cam_server_id,
        img_path
    ):

        self.cursor.execute("""
            INSERT INTO faces (
                id,
                name,
                cam_server_id,
                img_path
            )
            VALUES (?, ?, ?, ?)
        """, (
            face_id,
            name,
            cam_server_id,
            img_path
        ))

        self.conn.commit()

    # ======================================
    # SEARCH FACE IDS
    # ======================================

    def search_faces(self, info: Info):

        query = """
            SELECT
                id,
                name
            FROM faces
            WHERE 1=1
        """

        params = []

        if info.name is not None:
            query += " AND name=?"
            params.append(info.name)

        if info.cam_server_id is not None:
            query += " AND cam_server_id=?"
            params.append(info.cam_server_id)

        self.cursor.execute(
            query,
            tuple(params)
        )

        rows = self.cursor.fetchall()

        return rows


# ==========================================
# PINECONE DATABASE
# ==========================================

class PineconeFaceDB:

    def __init__(
        self,
        index_name
    ):

        api_key = os.getenv(
            "PINECONE_API_KEY"
        )

        if api_key is None:
            raise ValueError(
                "PINECONE_API_KEY not found in .env"
            )

        self.pc = Pinecone(
            api_key=api_key
        )

        self.index = self.pc.Index(
            index_name
        )

    # ======================================
    # INSERT VECTOR
    # ======================================

    def upsert_embedding(
        self,
        face_id,
        embedding,
        metadata
    ):

        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()

        self.index.upsert(
            vectors=[
                {
                    "id": face_id,
                    "values": embedding,
                    "metadata": metadata
                }
            ]
        )

    # ======================================
    # GET VECTOR BY ID
    # ======================================

    def get_embedding(self, face_id):

        result = self.index.fetch(
            ids=[face_id]
        )

        vectors = result.vectors

        if face_id not in vectors:
            return None

        vector = vectors[face_id]

        return np.array(
            vector.values,
            dtype=np.float32
        )

    # ======================================
    # SEARCH VECTOR
    # ======================================

    def search_embedding(
        self,
        embedding,
        top_k=1,
        cam_server_id=None
    ):

        if isinstance(embedding, np.ndarray):
            embedding = embedding.tolist()

        kwargs = {
            "vector": embedding,
            "top_k": top_k,
            "include_metadata": True
        }

        # FILTER
        if cam_server_id is not None:

            kwargs["filter"] = {
                "cam_server_id": {
                    "$eq": cam_server_id
                }
            }

        return self.index.query(
            **kwargs
        )


# ==========================================
# HYBRID FACE DB
# ==========================================

class HybridFaceDB(FRDb):

    def __init__(self, config: HybridConfig):

        # SQLITE
        sqlite_path = os.path.join(
            "./",
            config.sqlite_path
        )

        self.sql = SQLiteFaceDB(
            sqlite_path
        )

        # IMAGE DIR
        self.image_dir = os.path.join(
            "./",
            config.image_dir
        )

        os.makedirs(
            self.image_dir,
            exist_ok=True
        )

        # PINECONE
        self.vector = PineconeFaceDB(
            index_name=config.index_name
        )

    # ======================================
    # GET EMBEDDINGS
    # SQLITE -> IDS
    # PINECONE -> EMBEDDINGS
    # ======================================

    def getEmbedding(self, info: Info):

        rows = self.sql.search_faces(
            info
        )

        results = []

        for face_id, name in rows:

            embedding = self.vector.get_embedding(
                face_id
            )

            if embedding is None:
                continue

            results.append(
                (
                    embedding,
                    name
                )
            )

        return results

    # ======================================
    # INSERT FACE
    # ======================================

    def updateEmbedding(
        self,
        info: Info,
        embedding,
        img
    ):

        # UUID
        face_id = str(
            uuid.uuid4()
        )

        # SAVE IMAGE
        img_path = os.path.join(
            self.image_dir,
            f"{face_id}.jpg"
        )

        cv2.imwrite(
            img_path,
            img
        )

        # ==================================
        # SQLITE
        # ==================================

        self.sql.insert_face(
            face_id=face_id,
            name=info.name,
            cam_server_id=info.cam_server_id,
            img_path=img_path
        )

        # ==================================
        # PINECONE
        # ==================================

        self.vector.upsert_embedding(
            face_id=face_id,
            embedding=embedding,
            metadata={
                "name": info.name,
                "cam_server_id": info.cam_server_id
            }
        )

        return face_id

    # ======================================
    # DIRECT SEARCH
    # ======================================

    def search_face(
        self,
        embedding,
        cam_server_id=None,
        threshold=0.6
    ):

        result = self.vector.search_embedding(
            embedding=embedding,
            top_k=1,
            cam_server_id=cam_server_id
        )

        if len(result.matches) == 0:
            return None

        best_match = result.matches[0]

        if best_match.score < threshold:
            return None

        return {
            "face_id": best_match.id,
            "score": best_match.score,
            "metadata": best_match.metadata
        }