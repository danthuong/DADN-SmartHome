from dataclasses import dataclass

@dataclass
class Retina_ArcConfig:
    device: str = "cpu"
    det_size: int = 640
    scale: str = "s"

@dataclass
class JSONDbConfig:
    db_path: str = "frdb.json"
    image_dir: str = "images"