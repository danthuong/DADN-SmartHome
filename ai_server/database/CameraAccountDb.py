from abc import ABC, abstractmethod

class CameraAccountDb(ABC):

    @abstractmethod
    def get_servers(self, account):
        pass

import json
import os


class JSONCameraAccountDb(CameraAccountDb):

    def __init__(self, db_path="camera_accounts.json"):

        base_path = os.path.join("modules", "face_recognition")
        self.db_path = os.path.join(base_path, db_path)

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        if not os.path.exists(self.db_path):
            with open(self.db_path, "w") as f:
                json.dump([], f)

    def _load(self):
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except:
            return []

    def get_servers(self, account):

        data = self._load()

        for user in data:
            if user.get("account") == account:

                servers = user.get("servers", [])

                result = []

                for s in servers:
                    result.append({
                        "name": s.get("name"),
                        "cam_server_id": s.get("cam_server_id"),
                        "location": s.get("location"),
                        "url": s.get("url")
                    })

                return result

        return []