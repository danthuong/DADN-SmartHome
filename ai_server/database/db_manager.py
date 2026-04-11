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
