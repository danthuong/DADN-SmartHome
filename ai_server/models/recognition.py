from insightface.app  import FaceAnalysis
import torch
import numpy as np
from abc import ABC, abstractmethod
from modules.face_recognition.config.config import Retina_ArcConfig
import cv2

class ModelFactory:
    _registry = {}

    @classmethod
    def register(cls, name, model_cls, config_cls):
        cls._registry[name] = (model_cls, config_cls)

    @classmethod
    def create(cls, name, config):
        if name not in cls._registry:
            raise ValueError(f"Unknown model: {name}")

        model_cls, config_cls = cls._registry[name]

        if not isinstance(config, config_cls):
            raise TypeError(
                f"{name} requires config type {config_cls.__name__}"
            )

        return model_cls(config)

def register_model(name, config_cls):
    def decorator(model_cls):
        ModelFactory.register(name, model_cls, config_cls)
        return model_cls
    return decorator

class FRModel(ABC):
    @abstractmethod
    def detect(self, img):
        pass

@register_model("retina_arc", Retina_ArcConfig)
class Retina_ArcModel(FRModel):
    def __init__(self, config):
        self.device = torch.device(config.device)
        self.model = FaceAnalysis(name="buffalo_" + config.scale)
        self.det_size = config.det_size
        ctx_id = -1 if self.device.type == "cpu" else 0
        self.model.prepare(ctx_id=ctx_id, det_size=(self.det_size, self.det_size))
    
    def detect(self, img):
        return self.model.get(img)

