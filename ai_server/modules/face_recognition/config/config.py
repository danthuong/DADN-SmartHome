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

@dataclass
class HybridConfig:

    # SQLite database
    sqlite_path: str = "smart_home.db"

    # Folder save face images
    image_dir: str = "images"

    # Pinecone index name
    index_name: str = "faces"