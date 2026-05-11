from abc import ABC, abstractmethod
import sqlite3
import os


# ==========================================
# BASE CAMERA ACCOUNT DB
# ==========================================

class CameraAccountDb(ABC):

    @abstractmethod
    def get_servers(self, account):
        pass


# ==========================================
# SQLITE CAMERA ACCOUNT DB
# ==========================================

class SQLiteCameraAccountDb(CameraAccountDb):

    def __init__(self, db_path="smart_home.db"):
        self.db_path = os.path.join(
            "./",
            db_path
        )

        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )

        self.cursor = self.conn.cursor()

    # ======================================
    # GET SERVERS BY ACCOUNT
    # ======================================

    def get_servers(self, account):

        query = """
            SELECT
                s.cam_server_id,
                s.location,
                s.url
            FROM users u

            INNER JOIN user_servers us
                ON u.id = us.user_id

            INNER JOIN servers s
                ON us.cam_server_id = s.cam_server_id

            WHERE u.username = ?
        """

        self.cursor.execute(
            query,
            (account,)
        )

        rows = self.cursor.fetchall()

        result = []

        for row in rows:

            result.append({
                "cam_server_id": row[0],
                "location": row[1],
                "url": row[2]
            })

        return result