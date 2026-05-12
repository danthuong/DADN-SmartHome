import sqlite3
import json
import threading
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    def __init__(self, db_name="smart_home.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Cơ chế khóa luồng cực xịn của team Mobile
        self.lock = threading.RLock()
        
        # Bật khóa ngoại (Của team IoT)
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        
        for name in dir(self.__class__):
            if not name.startswith("_") and callable(getattr(self, name)):
                method = getattr(self, name)
                setattr(self, name, self._with_lock(method))
                
        self.create_tables()
        self.init_master_data()

    def _with_lock(self, method):
        def wrapper(*args, **kwargs):
            with self.lock:
                return method(*args, **kwargs)
        return wrapper

    def create_tables(self):
        # ==========================================
        # BẢNG CỦA TEAM MOBILE / WEB
        # ==========================================
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, avatar TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, device_id TEXT NOT NULL, name TEXT NOT NULL, type TEXT NOT NULL, room_id TEXT, state_json TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, room_id TEXT NOT NULL, name TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, preset_id TEXT, name TEXT NOT NULL, icon TEXT NOT NULL, room_id TEXT, device_configs_json TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # ==========================================
        # BẢNG CỦA TEAM IOT / CAMERA
        # ==========================================
        self.cursor.execute("CREATE TABLE IF NOT EXISTS cameras (camera_id TEXT PRIMARY KEY, location TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS sensors (sensor_id TEXT PRIMARY KEY, description TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, description TEXT)")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS faces (
            id TEXT PRIMARY KEY,
            name TEXT,
            cam_server_id TEXT,
            img_path TEXT,
            FOREIGN KEY (cam_server_id) REFERENCES servers(cam_server_id)
        )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_cameras (
                user_id INTEGER NOT NULL, camera_id TEXT NOT NULL,
                PRIMARY KEY (user_id, camera_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (camera_id) REFERENCES cameras(camera_id) ON DELETE CASCADE
            )
        """)

        # ==========================================
        # CÁC BẢNG LOGS (HỢP NHẤT HOÀN HẢO)
        # ==========================================
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS camera_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, camera_id TEXT NOT NULL, has_human INTEGER DEFAULT 0, face_id TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gesture_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, camera_id TEXT NOT NULL, gesture_name TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, sensor_id TEXT NOT NULL, value REAL, user_name TEXT DEFAULT 'N/A', timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id)
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, status INTEGER, trigger_source TEXT, threshold_used REAL DEFAULT 0, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        """)

        # ======================
        # SERVER CỦA TEAM MOBILE
        # ======================
        self.cursor.execute("CREATE TABLE IF NOT EXISTS servers (cam_server_id TEXT PRIMARY KEY, location TEXT, url TEXT)")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_servers (
            user_id INTEGER,
            cam_server_id TEXT,
            PRIMARY KEY (user_id, cam_server_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (cam_server_id) REFERENCES servers(cam_server_id)
        )
        """)
        self.conn.commit()

    def init_master_data(self):
        # Đã khôi phục SET_TEMP và SET_LIGHT cho IoT
        self.cursor.execute("INSERT OR IGNORE INTO cameras VALUES ('CAM_01', 'Phòng Khách')")
        sensors = [('AI_CAM', 'Camera AI nhận diện người'), ('PIR', 'Cảm biến hồng ngoại'), ('TEMP', 'Cảm biến nhiệt độ'), ('LIGHT', 'Cảm biến ánh sáng')]
        devices = [
            ('FAN', 'Quạt thông gió'), 
            ('LED', 'Đèn chiếu sáng'),
            ('SET_TEMP', 'Ngưỡng nhiệt độ (App)'),  
            ('SET_LIGHT', 'Ngưỡng ánh sáng (App)')  
        ]
        
        self.cursor.executemany("INSERT OR IGNORE INTO sensors VALUES (?,?)", sensors)
        self.cursor.executemany("INSERT OR IGNORE INTO devices VALUES (?,?)", devices)
        self.conn.commit()

    # ==========================================
    # CÁC HÀM GHI LOG (HỖ TRỢ CẢ MOBILE VÀ IOT)
    # ==========================================
    def log_sensor(self, sensor_id, value, user_name="N/A"):
        self.cursor.execute("INSERT INTO sensor_logs (sensor_id, value, user_name) VALUES (?, ?, ?)", (sensor_id, value, user_name))
        self.conn.commit()

    def log_camera(self, camera_id, has_human, face_id=None):
        self.cursor.execute("INSERT INTO camera_logs (camera_id, has_human, face_id) VALUES (?, ?, ?)", (camera_id, has_human, face_id))
        self.conn.commit()

    def log_gesture(self, camera_id, gesture_name):
        self.cursor.execute("INSERT INTO gesture_logs (camera_id, gesture_name) VALUES (?, ?)", (camera_id, gesture_name))
        self.conn.commit()

    def log_device(self, device_id, status, trigger_source, threshold=0):
        # Đổi tên biến về trigger_source để khớp với Logger Service
        self.cursor.execute(
            "INSERT INTO device_logs (device_id, status, trigger_source, threshold_used) VALUES (?, ?, ?, ?)",
            (device_id, status, trigger_source, threshold)
        )
        self.conn.commit()

    # =========================================================================
    # CÁC HÀM CÒN LẠI CỦA TEAM MOBILE (GIỮ NGUYÊN KHÔNG ĐỤNG CHẠM)
    # =========================================================================
    
    def migrate_database(self):
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass
        
        try:
            self.cursor.execute("ALTER TABLE user_presets ADD COLUMN preset_id TEXT")
            self.conn.commit()
        except sqlite3.OperationalError:
            pass

    def create_user(self, username, password):

        hashed = generate_password_hash(password)

        try:
            # 1. INSERT USER TRƯỚC
            self.cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed)
            )

            user_id = self.cursor.lastrowid   # ✅ LẤY ID NGAY SAU INSERT

            # 2. AUTO LINK CAMERA SERVERS
            self.cursor.execute("SELECT cam_server_id FROM servers")
            servers = self.cursor.fetchall()

            for (cam_server_id,) in servers:
                self.cursor.execute(
                    """
                    INSERT OR IGNORE INTO user_servers (user_id, cam_server_id)
                    VALUES (?, ?)
                    """,
                    (user_id, cam_server_id)
                )

            self.conn.commit()

            print(f"[OK] Auto linked {len(servers)} camera servers to user {username}")

            return {
                "success": True,
                "user_id": user_id
            }

        except sqlite3.IntegrityError:
            return {
                "success": False,
                "message": "Username already exists"
            }

    def get_user(self, username):
        self.cursor.execute("SELECT id, username, password, avatar FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "password": row[2], "avatar": row[3]}
        return None

    def update_user_avatar(self, user_id, avatar_data):
        self.cursor.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar_data, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_user_avatar(self, user_id):
        self.cursor.execute("SELECT avatar FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def verify_password(self, stored_password, provided_password):
        return check_password_hash(stored_password, provided_password)

    def add_user_device(self, user_id, device_id, name, device_type, room_id="LIVING", state_json=None):
        if state_json is None:
            if device_type == "light":
                state_json = json.dumps({"isOn": False, "brightness": 50, "color": -256})
            else:
                state_json = json.dumps({"isOn": False, "speed": 1, "isOscillating": False, "isTracking": False})
        
        self.cursor.execute(
            "INSERT INTO user_devices (user_id, device_id, name, type, room_id, state_json) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, device_id, name, device_type, room_id, state_json)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_devices(self, user_id):
        self.cursor.execute("SELECT id, device_id, name, type, room_id, state_json FROM user_devices WHERE user_id = ?", (user_id,))
        devices = []
        for row in self.cursor.fetchall():
            state = json.loads(row[5]) if row[5] else {}
            devices.append({"id": row[1], "name": row[2], "type": row[3], "roomId": row[4], **state})
        return devices

    def update_user_device(self, user_id, device_id, updates):
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id, device_id]
        if "state_json" in updates:
            set_clause = "state_json = ?"
            values = [updates["state_json"], user_id, device_id]
        self.cursor.execute(f"UPDATE user_devices SET {set_clause} WHERE user_id = ? AND device_id = ?", values)
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_user_device(self, user_id, device_id):
        self.cursor.execute("DELETE FROM user_devices WHERE user_id = ? AND device_id = ?", (user_id, device_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def add_user_room(self, user_id, room_id, name):
        self.cursor.execute("INSERT INTO user_rooms (user_id, room_id, name) VALUES (?, ?, ?)", (user_id, room_id, name))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_rooms(self, user_id):
        self.cursor.execute("SELECT room_id, name FROM user_rooms WHERE user_id = ?", (user_id,))
        rooms = [{"id": row[0], "name": row[1]} for row in self.cursor.fetchall()]
        if not rooms:
            default_rooms = [("LIVING", "Phòng khách"), ("BED", "Phòng ngủ"), ("KITCHEN", "Nhà bếp"), ("GARDEN", "Sân vườn")]
            for room_id, name in default_rooms:
                self.add_user_room(user_id, room_id, name)
            return self.get_user_rooms(user_id)
        return rooms

    def delete_user_room(self, user_id, room_id):
        self.cursor.execute("DELETE FROM user_rooms WHERE user_id = ? AND room_id = ?", (user_id, room_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def add_user_preset(self, user_id, preset_id, name, icon, room_id=None, device_configs_json=None):
        if device_configs_json is None:
            device_configs_json = "{}"
        self.cursor.execute(
            "INSERT INTO user_presets (user_id, preset_id, name, icon, room_id, device_configs_json) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, preset_id, name, icon, room_id, device_configs_json)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_presets(self, user_id):
        self.cursor.execute("SELECT preset_id, name, icon, room_id, device_configs_json FROM user_presets WHERE user_id = ?", (user_id,))
        presets = []
        for row in self.cursor.fetchall():
            configs = json.loads(row[4]) if row[4] else {}
            presets.append({"id": row[0], "name": row[1], "icon": row[2], "roomId": row[3], "deviceConfigs": configs})
        return presets

    def update_user_preset(self, user_id, preset_id, name=None, icon=None, room_id=None, device_configs_json=None):
        updates = {}
        if name: updates["name"] = name
        if icon: updates["icon"] = icon
        if room_id: updates["room_id"] = room_id
        if device_configs_json: updates["device_configs_json"] = device_configs_json
        
        if not updates: return False
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id, preset_id]
        
        self.cursor.execute(f"UPDATE user_presets SET {set_clause} WHERE user_id = ? AND preset_id = ?", values)
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_user_preset(self, user_id, preset_id):
        self.cursor.execute("DELETE FROM user_presets WHERE user_id = ? AND preset_id = ?", (user_id, preset_id))
        self.conn.commit()
        return self.cursor.rowcount > 0


if __name__ == "__main__":

    # print("=" * 50)
    # print(" SMART HOME DATABASE INITIALIZATION ")
    # print("=" * 50)

    # # ============================
    # # CREATE DB MANAGER
    # # ============================

    db = DatabaseManager("smart_home.db")

    # print("[OK] DatabaseManager initialized")

    # # ============================
    # # RUN MIGRATIONS
    # # ============================

    # print("\n[INFO] Running migrations...")

    # db.migrate_database()
    # print("[OK] Migration completed")

    # # ============================
    # # CREATE TEST USER
    # # ============================

    # print("\n[INFO] Creating test user...")

    # result = db.create_user(
    #     username="account1",
    #     password="123456789"
    # )

    # if result["success"]:
    #     print(f"[OK] User created with ID: {result['user_id']}")

    #     user_id = result["user_id"]

    # else:

    #     print(f"[INFO] {result['message']}")

    #     user = db.get_user("account1")

    #     user_id = user["id"]

    #     print(f"[OK] Existing user ID: {user_id}")

    # # ============================
    # # INIT DEFAULT ROOMS
    # # ============================

    # print("\n[INFO] Initializing rooms...")

    # rooms = db.get_user_rooms(user_id)

    # for room in rooms:
    #     print(f"   -> {room['id']} : {room['name']}")

    # # ============================
    # # ADD SAMPLE DEVICES
    # # ============================

    # print("\n[INFO] Adding sample devices...")

    # db.add_user_device(
    #     user_id=user_id,
    #     device_id="LED_001",
    #     name="Living Room LED",
    #     device_type="light",
    #     room_id="LIVING"
    # )

    # db.add_user_device(
    #     user_id=user_id,
    #     device_id="FAN_001",
    #     name="Bedroom Fan",
    #     device_type="fan",
    #     room_id="BED"
    # )

    # print("[OK] Sample devices added")

    # # ============================
    # # CREATE SAMPLE PRESET
    # # ============================

    # print("\n[INFO] Creating sample preset...")

    # sample_config = {
    #     "LED_001": {
    #         "isOn": True,
    #         "brightness": 80
    #     },
    #     "FAN_001": {
    #         "isOn": True,
    #         "speed": 3
    #     }
    # }

    # db.add_user_preset(
    #     user_id=user_id,
    #     preset_id="PRESET_SLEEP",
    #     name="Sleep Mode",
    #     icon="moon",
    #     room_id="BED",
    #     device_configs_json=json.dumps(sample_config)
    # )

    # print("[OK] Sample preset created")

    # # ============================
    # # INSERT SAMPLE LOGS
    # # ============================

    # print("\n[INFO] Inserting sample logs...")

    # db.log_sensor(
    #     sensor_id="TEMP",
    #     value=28.5,
    #     user_name="account"
    # )

    # db.log_sensor(
    #     sensor_id="LIGHT",
    #     value=300,
    #     user_name="account"
    # )

    # db.log_device(
    #     device_id="LED",
    #     status=1,
    #     trigger_source="Motion detected",
    #     threshold=0.8
    # )

    # db.log_device(
    #     device_id="FAN",
    #     status=1,
    #     trigger_source="Temperature high",
    #     threshold=30
    # )

    # print("[OK] Sample logs inserted")

    # # ============================
    # # SHOW DATA
    # # ============================

    # print("\n[INFO] Fetching user devices...")

    # devices = db.get_user_devices(user_id)

    # for device in devices:
    #     print(device)

    # print("\n[INFO] Fetching presets...")

    # presets = db.get_user_presets(user_id)

    # for preset in presets:
    #     print(preset)

    # # ============================
    # # DONE
    # # ============================

    # print("\n" + "=" * 50)
    # print(" DATABASE READY SUCCESSFULLY ")
    # print("=" * 50)
    result = db.create_user(
        username="account",
        password="123456789"
    )
