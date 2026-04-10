import sqlite3

class DatabaseManager:
    def __init__(self, db_name="smart_home.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        
        # Bật khóa ngoại (Foreign Key)
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        
        self.create_tables()
        self.init_master_data()

    def create_tables(self):
        # ==========================================
        # QUẢN LÍ NGƯỜI DÙNG VÀ FaceID
        # ==========================================
        self.cursor.execute("CREATE TABLE IF NOT EXISTS accounts (user_id TEXT PRIMARY KEY, user_name TEXT NOT NULL, password TEXT NOT NULL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS cameras (camera_id TEXT PRIMARY KEY, location TEXT)")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS faces (
                face_id TEXT PRIMARY KEY, camera_id TEXT NOT NULL, name TEXT, embedding_path TEXT,
                FOREIGN KEY (camera_id) REFERENCES cameras(camera_id) ON DELETE CASCADE
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS account_cameras (
                user_id TEXT NOT NULL, camera_id TEXT NOT NULL,
                PRIMARY KEY (user_id, camera_id),
                FOREIGN KEY (user_id) REFERENCES accounts(user_id) ON DELETE CASCADE,
                FOREIGN KEY (camera_id) REFERENCES cameras(camera_id) ON DELETE CASCADE
            )
        """)

        # ==========================================
        # DANH MỤC THIẾT BỊ VÀ CẢM BIẾN
        # ==========================================
        self.cursor.execute("CREATE TABLE IF NOT EXISTS sensors (sensor_id TEXT PRIMARY KEY, description TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, description TEXT)")

        # ==========================================
        # LOGs
        # ==========================================
        # 1. Log Camera (AI & FaceID)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS camera_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, camera_id TEXT NOT NULL, has_human INTEGER DEFAULT 0, face_id TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (camera_id) REFERENCES cameras(camera_id), FOREIGN KEY (face_id) REFERENCES faces(face_id)
            )
        """)
        # 2. Log Cử Chỉ (Team Motion)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gesture_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, camera_id TEXT NOT NULL, gesture_name TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
            )
        """)
        # 3. Log Cảm Biến YoloBit
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, sensor_id TEXT NOT NULL, value REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (sensor_id) REFERENCES sensors(sensor_id)
            )
        """)
        # 4. Log Thiết Bị
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT, device_id TEXT NOT NULL, status INTEGER, trigger_source TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(device_id)
            )
        """)
        self.conn.commit()

    def init_master_data(self):
        # Nạp sẵn Camera mặc định và các thiết bị IoT
        self.cursor.execute("INSERT OR IGNORE INTO cameras VALUES ('CAM_01', 'Phòng Khách')")
        sensors = [('PIR', 'Cảm biến hồng ngoại'), ('TEMP', 'Cảm biến nhiệt độ'), ('LIGHT', 'Cảm biến ánh sáng')]
        devices = [
            ('FAN', 'Quạt thông gió'), 
            ('LED', 'Đèn chiếu sáng'),
            ('SET_TEMP', 'Ngưỡng nhiệt độ (App)'),  # Thiết bị ảo 1 - tượng trưng ngưỡng
            ('SET_LIGHT', 'Ngưỡng ánh sáng (App)')  
        ]
        
        self.cursor.executemany("INSERT OR IGNORE INTO sensors VALUES (?,?)", sensors)
        self.cursor.executemany("INSERT OR IGNORE INTO devices VALUES (?,?)", devices)
        self.conn.commit()

    # ==========================================
    # CÁC HÀM GHI LOG
    # ==========================================
    def log_sensor(self, sensor_id, value):
        self.cursor.execute("INSERT INTO sensor_logs (sensor_id, value) VALUES (?, ?)", (sensor_id, value))
        self.conn.commit()

    def log_camera(self, camera_id, has_human, face_id=None):
        self.cursor.execute("INSERT INTO camera_logs (camera_id, has_human, face_id) VALUES (?, ?, ?)", (camera_id, has_human, face_id))
        self.conn.commit()

    def log_gesture(self, camera_id, gesture_name):
        self.cursor.execute("INSERT INTO gesture_logs (camera_id, gesture_name) VALUES (?, ?)", (camera_id, gesture_name))
        self.conn.commit()

    def log_device(self, device_id, status, trigger_source):
        self.cursor.execute("INSERT INTO device_logs (device_id, status, trigger_source) VALUES (?, ?, ?)", (device_id, status, trigger_source))
        self.conn.commit()