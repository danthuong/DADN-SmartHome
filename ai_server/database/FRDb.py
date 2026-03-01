import json
import os
import uuid
import numpy as np
import cv2
from abc import ABC, abstractmethod
from modules.face_recognition.config.config import JSONDbConfig
class Info:
    def __init__(self, name=None, location=None):
        self.name = name
        self.location = location

class DbFactory:
    _registry = {}

    @classmethod
    def register(cls, name, db_cls, config_cls):
        cls._registry[name] = (db_cls, config_cls)

    @classmethod
    def create(cls, name, config):
        if name not in cls._registry:
            raise ValueError(f"Unknown Database: {name}")

        db_cls, config_cls = cls._registry[name]

        if not isinstance(config, config_cls):
            raise TypeError(
                f"{name} requires config type {config_cls.__name__}"
            )

        return db_cls(config)

def register_db(name, config_cls):
    def decorator(db_cls):
        DbFactory.register(name, db_cls, config_cls)
        return db_cls
    return decorator

class FRDb(ABC):
    @abstractmethod
    def getEmbedding(self, info: Info):
        pass
    @abstractmethod
    def updateEmbedding(self, info: Info, embedding, img):
        pass

from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
@register_db("jsonDb", JSONDbConfig)
class JSON_FRDb(FRDb):
    def __init__(self, config):
        self.db_path = BASE_DIR / config.db_path
        self.image_dir = BASE_DIR / config.image_dir

        self.db_path = str(self.db_path)
        self.image_dir = str(self.image_dir)

        # Tạo file db nếu chưa tồn tại
        if not os.path.exists(self.db_path):
            with open(self.db_path, "w") as f:
                json.dump([], f)

        # Tạo thư mục lưu ảnh
        if not os.path.exists(self.image_dir):
            os.makedirs(self.image_dir)

    def _load(self):
        with open(self.db_path, "r") as f:
            return json.load(f)

    def _save(self, data):
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

    def _match(self, record, info: Info):
        if info.name is not None and record["name"] != info.name:
            return False
        if info.location is not None and record["location"] != info.location:
            return False
        return True

    def getEmbedding(self, info: Info):
        data = self._load()
        results = []

        for record in data:
            if self._match(record, info):
                results.append(
                    (
                        np.array(record["embedding"], dtype=np.float32),
                        record["name"]
                    )
                    )

        return results

    def updateEmbedding(self, info: Info, embedding, img):
        data = self._load()

        # Sinh ID duy nhất
        image_id = str(uuid.uuid4())

        # Tạo path lưu ảnh
        img_path = os.path.join(self.image_dir, f"{image_id}.jpg")

        # Lưu ảnh
        cv2.imwrite(img_path, img)

        record = {
            "id": image_id,  # khóa chính
            "name": info.name,
            "location": info.location,
            "img_path": img_path,
            "embedding": embedding.tolist()
        }

        data.append(record)
        self._save(data)

        return image_id

