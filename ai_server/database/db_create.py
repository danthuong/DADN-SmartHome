import sqlite3
import uuid
import json

class DatabaseCreator:
    def __init__(self, db_path="smart_home.db"):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):

        # ======================
        # USER
        # ======================
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT
        )
        """)

        # ======================
        # SERVER
        # ======================
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            cam_server_id TEXT PRIMARY KEY,
            location TEXT,
            url TEXT
        )
        """)

        # ======================
        # FACE
        # ======================
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS faces (
            id TEXT PRIMARY KEY,
            name TEXT,
            cam_server_id TEXT,
            img_path TEXT,
            FOREIGN KEY (cam_server_id) REFERENCES servers(cam_server_id)
        )
        """)

        # ======================
        # USER ↔ SERVER
        # ======================
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_servers (
            user_id TEXT,
            cam_server_id TEXT,
            PRIMARY KEY (user_id, cam_server_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (cam_server_id) REFERENCES servers(cam_server_id)
        )
        """)

        self.conn.commit()
    
    def seed_initial_data(self):

        # ======================
        # INIT USER DATA
        # ======================
        data = [
            {
                "account": "account",
                "pwd": "123456789",
                "servers": [
                    {
                        "cam_server_id": "server_221b",
                        "location": "221B Baker Street, Marylebone, London, UK",
                        "url": "http://localhost:9000"
                    }
                ]
            }
        ]

        for user in data:

            user_id = str(uuid.uuid4())

            # insert user
            self.cursor.execute("""
                INSERT OR IGNORE INTO users (id, username, password)
                VALUES (?, ?, ?)
            """, (user_id, user["account"], user["pwd"]))

            # insert servers + mapping
            for server in user["servers"]:

                cam_server_id = server["cam_server_id"]

                self.cursor.execute("""
                    INSERT OR IGNORE INTO servers (cam_server_id, location, url)
                    VALUES (?, ?, ?)
                """, (
                    cam_server_id,
                    server["location"],
                    server["url"]
                ))

                self.cursor.execute("""
                    INSERT OR IGNORE INTO user_servers (user_id, cam_server_id)
                    VALUES (?, ?)
                """, (
                    user_id,
                    cam_server_id
                ))

        self.conn.commit()

if __name__ == "__main__":

    print("Creating database...")

    db = DatabaseCreator("smart_home.db")

    print("Seeding initial data...")

    db.seed_initial_data()

    print("DONE ✅ Database ready!")