import sqlite3

class DatabaseManager:
    def __init__(self, db_name="smart_home.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Bảng lưu nhật ký cảm biến
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_type TEXT,
                value REAL,
                user_name TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Bảng lưu nhật ký thiết bị - ĐÃ THÊM CỘT threshold_used
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT,
                status INTEGER,      -- 0: OFF, 1: ON
                reason TEXT,         
                threshold_used REAL, -- Cột này nãy bạn bị thiếu nè!
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def log_sensor(self, sensor_type, value, user_name="N/A"):
        self.cursor.execute(
            "INSERT INTO sensor_logs (sensor_type, value, user_name) VALUES (?, ?, ?)",
            (sensor_type, value, user_name)
        )
        self.conn.commit()

    def log_device(self, device_name, status, reason, threshold=0):
        self.cursor.execute(
            "INSERT INTO device_logs (device_name, status, reason, threshold_used) VALUES (?, ?, ?, ?)",
            (device_name, status, reason, threshold)
        )
        self.conn.commit()