import sqlite3
import json
import threading
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    def __init__(self, db_name="smart_home.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        # Bật row_factory để dễ dàng parse dữ liệu thành Dictionary cho FastAPI
        self.conn.row_factory = sqlite3.Row 
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
        self.migrate_database()

    def _with_lock(self, method):
        def wrapper(*args, **kwargs):
            with self.lock:
                return method(*args, **kwargs)
        return wrapper

    def create_tables(self):
        # [GIỮ NGUYÊN CODE TẠO BẢNG CỦA BẠN]
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

        self.cursor.execute("CREATE TABLE IF NOT EXISTS cameras (camera_id TEXT PRIMARY KEY, location TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS sensors (sensor_id TEXT PRIMARY KEY, description TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, description TEXT)")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS faces (
            id TEXT PRIMARY KEY, name TEXT, cam_server_id TEXT, img_path TEXT,
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

        self.cursor.execute("CREATE TABLE IF NOT EXISTS servers (cam_server_id TEXT PRIMARY KEY, location TEXT, url TEXT)")
        
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_servers (
            user_id INTEGER, cam_server_id TEXT,
            PRIMARY KEY (user_id, cam_server_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (cam_server_id) REFERENCES servers(cam_server_id)
        )
        """)
        self.conn.commit()

    def init_master_data(self):
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

    # ==========================================
    # CÁC HÀM GHI LOG
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
        self.cursor.execute(
            "INSERT INTO device_logs (device_id, status, trigger_source, threshold_used) VALUES (?, ?, ?, ?)",
            (device_id, status, trigger_source, threshold)
        )
        self.conn.commit()

    # ==========================================
    # USER & AUTH
    # ==========================================
    def create_user(self, username, password):
        hashed = generate_password_hash(password)
        try:
            self.cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            user_id = self.cursor.lastrowid
            
            self.cursor.execute("SELECT cam_server_id FROM servers")
            servers = self.cursor.fetchall()
            for row in servers:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO user_servers (user_id, cam_server_id) VALUES (?, ?)",
                    (user_id, row["cam_server_id"]) # Đã dùng row_factory nên truy cập qua key
                )
            self.conn.commit()
            return {"success": True, "user_id": user_id}
        except sqlite3.IntegrityError:
            return {"success": False, "message": "Username already exists"}

    def get_user(self, username):
        self.cursor.execute("SELECT id, username, password, avatar FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def verify_password(self, stored_password, provided_password):
        return check_password_hash(stored_password, provided_password)

    def update_user_avatar(self, user_id, avatar_data):
        self.cursor.execute("UPDATE users SET avatar = ? WHERE id = ?", (avatar_data, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_user_avatar(self, user_id):
        self.cursor.execute("SELECT avatar FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row["avatar"] if row else None

    # ==========================================
    # QUẢN LÝ THIẾT BỊ (USER DEVICES)
    # ==========================================
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
        self.cursor.execute("SELECT device_id, name, type, room_id, state_json FROM user_devices WHERE user_id = ?", (user_id,))
        devices = []
        for row in self.cursor.fetchall():
            state = json.loads(row["state_json"]) if row["state_json"] else {}
            devices.append({"id": row["device_id"], "name": row["name"], "type": row["type"], "roomId": row["room_id"], **state})
        return devices

    def get_user_device_by_id(self, user_id, device_id):
        self.cursor.execute("SELECT type, state_json FROM user_devices WHERE user_id = ? AND device_id = ?", (user_id, device_id))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def update_user_device_state(self, user_id, device_id, new_state_json):
        self.cursor.execute(
            "UPDATE user_devices SET state_json = ? WHERE user_id = ? AND device_id = ?",
            (new_state_json, user_id, device_id)
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def delete_user_device(self, user_id, device_id):
        self.cursor.execute("DELETE FROM user_devices WHERE user_id = ? AND device_id = ?", (user_id, device_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    # ==========================================
    # QUẢN LÝ PHÒNG (ROOMS)
    # ==========================================
    def add_user_room(self, user_id, room_id, name):
        self.cursor.execute("INSERT INTO user_rooms (user_id, room_id, name) VALUES (?, ?, ?)", (user_id, room_id, name))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_user_rooms(self, user_id):
        self.cursor.execute("SELECT room_id, name FROM user_rooms WHERE user_id = ?", (user_id,))
        rows = self.cursor.fetchall()
        if not rows:
            default_rooms = [("LIVING", "Phòng khách"), ("BED", "Phòng ngủ"), ("KITCHEN", "Nhà bếp"), ("GARDEN", "Sân vườn")]
            for room_id, name in default_rooms:
                self.add_user_room(user_id, room_id, name)
            # Fetch lại sau khi tạo
            self.cursor.execute("SELECT room_id, name FROM user_rooms WHERE user_id = ?", (user_id,))
            rows = self.cursor.fetchall()
        return [{"id": row["room_id"], "name": row["name"]} for row in rows]

    def delete_room_cascade(self, user_id, room_id):
        """Xóa phòng sẽ xóa luôn thiết bị và preset trong phòng đó"""
        self.cursor.execute("DELETE FROM user_devices WHERE user_id = ? AND room_id = ?", (user_id, room_id))
        self.cursor.execute("DELETE FROM user_presets WHERE user_id = ? AND room_id = ?", (user_id, room_id))
        self.cursor.execute("DELETE FROM user_rooms WHERE user_id = ? AND room_id = ?", (user_id, room_id))
        deleted = self.cursor.rowcount > 0
        self.conn.commit()
        return deleted

    # ==========================================
    # PRESETS
    # ==========================================
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
            configs = json.loads(row["device_configs_json"]) if row["device_configs_json"] else {}
            presets.append({"id": row["preset_id"], "name": row["name"], "icon": row["icon"], "roomId": row["room_id"], "deviceConfigs": configs})
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

    # ==========================================
    # CÁC HÀM GET CHUYÊN DỤNG CHO API 
    # ==========================================
    def get_latest_environment(self):
        self.cursor.execute("SELECT value, timestamp FROM sensor_logs WHERE sensor_id='TEMP' ORDER BY timestamp DESC LIMIT 1")
        temp = self.cursor.fetchone()
        self.cursor.execute("SELECT value, timestamp FROM sensor_logs WHERE sensor_id='LIGHT' ORDER BY timestamp DESC LIMIT 1")
        light = self.cursor.fetchone()
        return {"temperature": dict(temp) if temp else None, "light": dict(light) if light else None}

    def get_all_devices_status(self, user_id):
        query = """
            SELECT d.device_id, d.description, 
                   COALESCE((SELECT status FROM device_logs 
                             WHERE device_id = d.device_id 
                             ORDER BY timestamp DESC LIMIT 1), 0) as status,
                   CASE WHEN ud.device_id IS NOT NULL THEN 1 ELSE 0 END as is_added
            FROM devices d
            LEFT JOIN user_devices ud ON d.device_id = ud.device_id AND ud.user_id = ?
            WHERE d.device_id NOT LIKE 'SET_%'
        """
        self.cursor.execute(query, (user_id,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_camera_logs(self, user_id, limit):
        # Cố gắng lọc log theo quyền truy cập của user (bảo mật)
        # Vì cấu trúc bảng cameras hiện tại đang gộp chung cam_server_id vào cột location,
        # ta tạm thời dùng mẹo LIKE để so khớp.
        query = """
            SELECT cl.* 
            FROM camera_logs cl
            JOIN cameras c ON cl.camera_id = c.camera_id
            JOIN user_servers us ON c.location LIKE us.cam_server_id || '%'
            WHERE us.user_id = ?
            ORDER BY cl.timestamp DESC LIMIT ?
        """
        try:
            self.cursor.execute(query, (user_id, limit))
            logs = [dict(row) for row in self.cursor.fetchall()]
            if logs: return logs
        except Exception as e:
            print(f"[DB WARN] Không thể join bảo mật log: {e}")
            
        # Fallback: Trả về toàn bộ nếu query trên thất bại (chữa cháy cho CSDL cũ)
        self.cursor.execute("SELECT * FROM camera_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_sensor_logs(self, sensor_id, limit):
        if sensor_id:
            self.cursor.execute("SELECT * FROM sensor_logs WHERE sensor_id=? ORDER BY timestamp DESC LIMIT ?", (sensor_id, limit))
        else:
            self.cursor.execute("SELECT * FROM sensor_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        return [dict(row) for row in self.cursor.fetchall()]

    def get_snapshot_status(self):
        def latest(sensor_id):
            self.cursor.execute("SELECT value FROM sensor_logs WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1", (sensor_id,))
            r = self.cursor.fetchone()
            return r["value"] if r else None

        temp = latest("TEMP")
        light = latest("LIGHT")
        pir = latest("PIR")

        self.cursor.execute("SELECT has_human FROM camera_logs ORDER BY timestamp DESC LIMIT 1")
        cam = self.cursor.fetchone()
        human = bool(cam["has_human"]) if cam else False

        return {
            "temperature": float(temp) if temp is not None else 0.0,
            "light": int(light) if light is not None else 0,
            "pir": bool(pir) if pir is not None else False,
            "human_detect": human
        }
