import sqlite3
import os
from datetime import datetime

# Lấy đường dẫn tuyệt đối đến thư mục chứa file này để lưu DB
DB_PATH = os.path.join(os.path.dirname(__file__), 'system_db.sqlite3')

class DatabaseManager:
    def __init__(self):
        # Mở kết nối (Tự tạo file DB nếu chưa có)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        """Khởi tạo 3 bảng để phục vụ 2 Use-case"""
        
        # 1. BẢNG NHẬT KÝ MÔI TRƯỜNG & HIỆN DIỆN (Environment_Logs)
        # -> Phục vụ: Ghi lại trạng thái người và giá trị cảm biến
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Environment_Logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                presence_status INTEGER,   -- 1 (Có), 0 (Không)
                temperature REAL,          -- Nhiệt độ (VD: 32.5)
                light_level REAL           -- Ánh sáng (VD: 15.0)
            )
        ''')

        # 2. BẢNG THIẾT LẬP THÔNG SỐ (Device_Settings)
        # -> Phục vụ UC-AEC-01: Lưu ngưỡng nhiệt độ, ánh sáng, thời gian đếm ngược
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS Device_Settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_name TEXT UNIQUE,
                setting_value REAL,
                updated_at DATETIME
            )
        ''')
        # Thêm sẵn một vài thông số mặc định nếu bảng trống
        self.cursor.execute("INSERT OR IGNORE INTO Device_Settings (setting_name, setting_value, updated_at) VALUES ('temp_threshold', 30.0, CURRENT_TIMESTAMP)")
        self.cursor.execute("INSERT OR IGNORE INTO Device_Settings (setting_name, setting_value, updated_at) VALUES ('light_threshold', 20.0, CURRENT_TIMESTAMP)")
        self.cursor.execute("INSERT OR IGNORE INTO Device_Settings (setting_name, setting_value, updated_at) VALUES ('timeout_seconds', 10.0, CURRENT_TIMESTAMP)")

        # 3. BẢNG CẢNH BÁO HỆ THỐNG (System_Alerts)
        # -> Phục vụ Ngoại lệ E1: Lưu các lỗi khi cảm biến hỏng (NaN)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS System_Alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME,
                error_source TEXT,         -- Nơi xảy ra lỗi (VD: Sensor_DHT)
                error_message TEXT         -- Chi tiết lỗi
            )
        ''')
        
        self.conn.commit()
        print("[DATABASE] Đã khởi tạo các bảng CSDL thành công!")

    # ==========================================
    # CÁC HÀM XỬ LÝ ĐỂ MAIN.PY GỌI RA DÙNG
    # ==========================================
    
    def log_environment(self, presence, temp=None, light=None):
        """Ghi nhận log vào CSDL (Gọi khi có thay đổi trạng thái)"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO Environment_Logs (timestamp, presence_status, temperature, light_level)
            VALUES (?, ?, ?, ?)
        ''', (now, presence, temp, light))
        self.conn.commit()

    def log_alert(self, source, message):
        """Ghi nhận cảnh báo lỗi phần cứng"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO System_Alerts (timestamp, error_source, error_message)
            VALUES (?, ?, ?)
        ''', (now, source, message))
        self.conn.commit()

    def get_setting(self, setting_name):
        """Lấy một thông số cấu hình ra"""
        self.cursor.execute('SELECT setting_value FROM Device_Settings WHERE setting_name = ?', (setting_name,))
        result = self.cursor.fetchone()
        return result[0] if result else None