import sqlite3
class DatabaseManager:
    def __init__(self, db_name="smart_home.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_master_data() # Thêm hàm khởi tạo danh mục

    def create_tables(self):
        # 1. Bảng Thực thể Sensor
        self.cursor.execute("CREATE TABLE IF NOT EXISTS sensors (sensor_id TEXT PRIMARY KEY, description TEXT)")
        
        # 2. Bảng Thực thể Device
        self.cursor.execute("CREATE TABLE IF NOT EXISTS devices (device_id TEXT PRIMARY KEY, description TEXT)")

        # 3. Bảng Log Sensor (Có FK trỏ về bảng sensors)
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

        # 4. Bảng Log Device (Có FK trỏ về bảng devices)
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
        # Tự động thêm các thực thể vào nếu chưa có
        sensors = [('AI_CAM', 'Camera AI nhận diện người'), ('PIR', 'Cảm biến hồng ngoại'), 
                   ('TEMP', 'Cảm biến nhiệt độ'), ('LIGHT', 'Cảm biến ánh sáng')]
        devices = [('FAN', 'Quạt thông gió'), ('LED', 'Đèn chiếu sáng')]
        
        self.cursor.executemany("INSERT OR IGNORE INTO sensors VALUES (?,?)", sensors)
        self.cursor.executemany("INSERT OR IGNORE INTO devices VALUES (?,?)", devices)
        self.conn.commit()

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