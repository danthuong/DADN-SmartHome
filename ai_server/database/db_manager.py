import sqlite3
import json
import threading
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    def __init__(self, db_name="smart_home.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.lock = threading.RLock()
        
        # Tự động bọc tất cả public methods bằng RLock để tránh lỗi đa luồng (Recursive cursors / database locked)
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
        # 1. Bảng Users (thêm avatar column)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                avatar TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Bảng User's Devices
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                device_id TEXT NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                room_id TEXT,
                state_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 3. Bảng User's Rooms
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                room_id TEXT NOT NULL,
                name TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 3b. Bảng User's Presets
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_presets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                icon TEXT NOT NULL,
                room_id TEXT,
                device_configs_json TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # 4. Bảng Thực thể Sensor
        self.cursor.execute("CREATE TABLE IF NOT EXISTS sensors (sensor_id TEXT PRIMARY KEY, description TEXT)")
        
        # 5. Bảng Thực thể Device
        self.cursor.execute("CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, description TEXT)")

        # 6. Bảng Log Sensor
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT,
                value REAL,
                user_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id)
            )
        """)

        # 7. Bảng Log Device
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT,
                status INTEGER,
                reason TEXT,
                threshold_used REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        """)

        # ======================
        # SERVER (from Camera module)
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
            user_id INTEGER,
            cam_server_id TEXT,
            PRIMARY KEY (user_id, cam_server_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (cam_server_id) REFERENCES servers(cam_server_id)
        )
        """)
        self.conn.commit()

    def init_master_data(self):
        sensors = [('AI_CAM', 'Camera AI nhận diện người'), ('PIR', 'Cảm biến hồng ngoại'), 
                   ('TEMP', 'Cảm biến nhiệt độ'), ('LIGHT', 'Cảm biến ánh sáng')]
        devices = [('FAN', 'Quạt thông gió'), ('LED', 'Đèn chiếu sáng')]
        
        self.cursor.executemany("INSERT OR IGNORE INTO sensors VALUES (?,?)", sensors)
        self.cursor.executemany("INSERT OR IGNORE INTO devices VALUES (?,?)", devices)
        self.conn.commit()

    def migrate_database(self):
        # Thêm cột avatar vào users nếu chưa có
        try:
            self.cursor.execute("ALTER TABLE users ADD COLUMN avatar TEXT")
            self.conn.commit()
            print("[MIGRATION] Added avatar column to users table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"[MIGRATION] avatar column already exists or error: {e}")
        
        # Thêm cột preset_id vào user_presets nếu chưa có (để lưu UUID từ mobile)
        try:
            self.cursor.execute("ALTER TABLE user_presets ADD COLUMN preset_id TEXT")
            self.conn.commit()
            print("[MIGRATION] Added preset_id column to user_presets table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"[MIGRATION] preset_id column already exists or error: {e}")

    # ==================== USER AUTH ====================
    def create_user(self, username, password):
        hashed = generate_password_hash(password)
        try:
            self.cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, hashed)
            )
            self.conn.commit()
            return {"success": True, "user_id": self.cursor.lastrowid}
        except sqlite3.IntegrityError:
            return {"success": False, "message": "Username already exists"}

    def get_user(self, username):
        self.cursor.execute("SELECT id, username, password, avatar FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        if row:
            return {"id": row[0], "username": row[1], "password": row[2], "avatar": row[3]}
        return None

    def update_user_avatar(self, user_id, avatar_data):
        self.cursor.execute(
            "UPDATE users SET avatar = ? WHERE id = ?",
            (avatar_data, user_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_user_avatar(self, user_id):
        self.cursor.execute("SELECT avatar FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def verify_password(self, stored_password, provided_password):
        return check_password_hash(stored_password, provided_password)

    # ==================== USER DEVICES ====================
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
        self.cursor.execute(
            "SELECT id, device_id, name, type, room_id, state_json FROM user_devices WHERE user_id = ?",
            (user_id,)
        )
        devices = []
        for row in self.cursor.fetchall():
            state = json.loads(row[5]) if row[5] else {}
            devices.append({
                "id": row[1],
                "name": row[2],
                "type": row[3],
                "roomId": row[4],
                **state
            })
        return devices

    def update_user_device(self, user_id, device_id, updates):
        # updates is a dict like {"name": "New Name"} or {"isOn": true}
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id, device_id]
        
        # Handle state_json specially
        if "state_json" in updates:
            set_clause = "state_json = ?"
            values = [updates["state_json"], user_id, device_id]
        
        self.cursor.execute(
            f"UPDATE user_devices SET {set_clause} WHERE user_id = ? AND device_id = ?",
            values
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_user_device(self, user_id, device_id):
        self.cursor.execute(
            "DELETE FROM user_devices WHERE user_id = ? AND device_id = ?",
            (user_id, device_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ==================== USER ROOMS ====================
    def add_user_room(self, user_id, room_id, name):
        self.cursor.execute(
            "INSERT INTO user_rooms (user_id, room_id, name) VALUES (?, ?, ?)",
            (user_id, room_id, name)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_rooms(self, user_id):
        self.cursor.execute(
            "SELECT room_id, name FROM user_rooms WHERE user_id = ?",
            (user_id,)
        )
        rooms = []
        for row in self.cursor.fetchall():
            rooms.append({"id": row[0], "name": row[1]})
        
        # Add default rooms if none exist
        if not rooms:
            default_rooms = [
                ("LIVING", "Phòng khách"),
                ("BED", "Phòng ngủ"),
                ("KITCHEN", "Nhà bếp"),
                ("GARDEN", "Sân vườn")
            ]
            for room_id, name in default_rooms:
                self.add_user_room(user_id, room_id, name)
            return self.get_user_rooms(user_id)
        
        return rooms

    def delete_user_room(self, user_id, room_id):
        self.cursor.execute(
            "DELETE FROM user_rooms WHERE user_id = ? AND room_id = ?",
            (user_id, room_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ==================== USER PRESETS ====================
    def add_user_preset(self, user_id, preset_id, name, icon, room_id=None, device_configs_json=None):
        if device_configs_json is None:
            device_configs_json = "{}"
        
        self.cursor.execute(
            "INSERT INTO user_presets (user_id, preset_id, name, icon, room_id, device_configs_json) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, preset_id, name, icon, room_id, device_configs_json)
        )
        self.conn.commit()
        print(f"[DB] Added preset: {preset_id}, name: {name}")
        return self.cursor.lastrowid

    def get_user_presets(self, user_id):
        self.cursor.execute(
            "SELECT preset_id, name, icon, room_id, device_configs_json FROM user_presets WHERE user_id = ?",
            (user_id,)
        )
        presets = []
        for row in self.cursor.fetchall():
            configs = json.loads(row[4]) if row[4] else {}
            presets.append({
                "id": row[0],
                "name": row[1],
                "icon": row[2],
                "roomId": row[3],
                "deviceConfigs": configs
            })
        print(f"[DB] Fetched {len(presets)} presets for user {user_id}")
        return presets

    def update_user_preset(self, user_id, preset_id, name=None, icon=None, room_id=None, device_configs_json=None):
        updates = {}
        if name:
            updates["name"] = name
        if icon:
            updates["icon"] = icon
        if room_id:
            updates["room_id"] = room_id
        if device_configs_json:
            updates["device_configs_json"] = device_configs_json
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_id, preset_id]
        
        self.cursor.execute(
            f"UPDATE user_presets SET {set_clause} WHERE user_id = ? AND preset_id = ?",
            values
        )
        self.conn.commit()
        print(f"[DB] Updated preset: {preset_id}")
        return self.cursor.rowcount > 0

    def delete_user_preset(self, user_id, preset_id):
        self.cursor.execute(
            "DELETE FROM user_presets WHERE user_id = ? AND preset_id = ?",
            (user_id, preset_id)
        )
        self.conn.commit()
        print(f"[DB] Deleted preset: {preset_id}")
        return self.cursor.rowcount > 0

    # ==================== EXISTING FUNCTIONS ====================
    def log_sensor(self, sensor_id, value, user_name="N/A"):
        self.cursor.execute(
            "INSERT INTO sensor_logs (sensor_id, value, user_name) VALUES (?, ?, ?)",
            (sensor_id, value, user_name)
        )
        self.conn.commit()

    def log_device(self, device_id, status, reason, threshold=0):
        self.cursor.execute(
            "INSERT INTO device_logs (device_id, status, reason, threshold_used) VALUES (?, ?, ?, ?)",
            (device_id, status, reason, threshold)
        )
        self.conn.commit()

    def init_camera_module(self):
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

            # =========================
            # 1. CHECK OR CREATE USER
            # =========================
            self.cursor.execute(
                "SELECT id FROM users WHERE username = ?",
                (user["account"],)
            )
            row = self.cursor.fetchone()

            if row:
                user_id = row[0]
            else:
                self.cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (user["account"], user["pwd"])
                )
                self.conn.commit()
                user_id = self.cursor.lastrowid

            # =========================
            # 2. INSERT SERVERS + MAP
            # =========================
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
        print("[OK] Camera module initialized (self-contained)")


if __name__ == "__main__":

    print("=" * 50)
    print(" SMART HOME DATABASE INITIALIZATION ")
    print("=" * 50)

    # ============================
    # CREATE DB MANAGER
    # ============================

    db = DatabaseManager("smart_home.db")

    print("[OK] DatabaseManager initialized")

    # ============================
    # RUN MIGRATIONS
    # ============================

    print("\n[INFO] Running migrations...")

    db.migrate_database()

    db.init_camera_module()

    print("[OK] Migration completed")

    # ============================
    # CREATE TEST USER
    # ============================

    print("\n[INFO] Creating test user...")

    result = db.create_user(
        username="account",
        password="123456789"
    )

    if result["success"]:
        print(f"[OK] User created with ID: {result['user_id']}")

        user_id = result["user_id"]

    else:

        print(f"[INFO] {result['message']}")

        user = db.get_user("account")

        user_id = user["id"]

        print(f"[OK] Existing user ID: {user_id}")

    # ============================
    # INIT DEFAULT ROOMS
    # ============================

    print("\n[INFO] Initializing rooms...")

    rooms = db.get_user_rooms(user_id)

    for room in rooms:
        print(f"   -> {room['id']} : {room['name']}")

    # ============================
    # ADD SAMPLE DEVICES
    # ============================

    print("\n[INFO] Adding sample devices...")

    db.add_user_device(
        user_id=user_id,
        device_id="LED_001",
        name="Living Room LED",
        device_type="light",
        room_id="LIVING"
    )

    db.add_user_device(
        user_id=user_id,
        device_id="FAN_001",
        name="Bedroom Fan",
        device_type="fan",
        room_id="BED"
    )

    print("[OK] Sample devices added")

    # ============================
    # CREATE SAMPLE PRESET
    # ============================

    print("\n[INFO] Creating sample preset...")

    sample_config = {
        "LED_001": {
            "isOn": True,
            "brightness": 80
        },
        "FAN_001": {
            "isOn": True,
            "speed": 3
        }
    }

    db.add_user_preset(
        user_id=user_id,
        preset_id="PRESET_SLEEP",
        name="Sleep Mode",
        icon="moon",
        room_id="BED",
        device_configs_json=json.dumps(sample_config)
    )

    print("[OK] Sample preset created")

    # ============================
    # INSERT SAMPLE LOGS
    # ============================

    print("\n[INFO] Inserting sample logs...")

    db.log_sensor(
        sensor_id="TEMP",
        value=28.5,
        user_name="account"
    )

    db.log_sensor(
        sensor_id="LIGHT",
        value=300,
        user_name="account"
    )

    db.log_device(
        device_id="LED",
        status=1,
        reason="Motion detected",
        threshold=0.8
    )

    db.log_device(
        device_id="FAN",
        status=1,
        reason="Temperature high",
        threshold=30
    )

    print("[OK] Sample logs inserted")

    # ============================
    # SHOW DATA
    # ============================

    print("\n[INFO] Fetching user devices...")

    devices = db.get_user_devices(user_id)

    for device in devices:
        print(device)

    print("\n[INFO] Fetching presets...")

    presets = db.get_user_presets(user_id)

    for preset in presets:
        print(preset)

    # ============================
    # DONE
    # ============================

    print("\n" + "=" * 50)
    print(" DATABASE READY SUCCESSFULLY ")
    print("=" * 50)