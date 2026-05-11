from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
# ==========================================
# 1. CẤU HÌNH SMART MQTT (Giao thức lõi)
# ==========================================
# Sử dụng class SmartHomeMQTT từ mqtt_client.py để bắn lệnh siêu tốc
from mqtt_client import SmartHomeMQTT

print("[API SERVER] Đang khởi tạo kết nối MQTT ngầm...")
mqtt = SmartHomeMQTT()
mqtt.start() 

# =========================================
# 2. CẤU HÌNH BẢO MẬT & JWT TOKEN
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("HS256")

# ==========================================
# 3. KHỞI TẠO FASTAPI SERVER
# ==========================================
app = FastAPI(
    title="Smart Home API - Distributed Architecture",
    description="Hệ thống API điều khiển và giám sát nhà thông minh qua MQTT",
    version="2.0.0"
)

# ==========================================
# 4. MODELS (Khuôn mẫu dữ liệu)
# ==========================================
class UserRegister(BaseModel):
    user_id: str
    user_name: str
    password: str

class UserLogin(BaseModel):
    user_name: str
    password: str

class DeviceControl(BaseModel):
    status: int  # 1 (Bật) hoặc 0 (Tắt)
    trigger_source: str = "Manual_App"

# ==========================================
# 5. HÀM HỖ TRỢ KẾT NỐI DATABASE
# ==========================================
def get_db_connection():
    conn = sqlite3.connect("smart_home.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row 
    return conn

# ==========================================
# NHÓM 1: XÁC THỰC TÀI KHOẢN (AUTH)
# ==========================================
@app.post("/api/auth/register", tags=["Authentication"])
def register_user(user: UserRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE user_id=? OR user_name=?", (user.user_id, user.user_name))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User ID hoặc Username đã tồn tại!")
    
    hashed_password = pwd_context.hash(user.password)
    cursor.execute("INSERT INTO accounts (user_id, user_name, password) VALUES (?, ?, ?)",
                   (user.user_id, user.user_name, hashed_password))
    conn.commit()
    conn.close()
    return {"message": f"Đăng ký thành công tài khoản: {user.user_name}"}

@app.post("/api/auth/login", tags=["Authentication"])
def login_user(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM accounts WHERE user_name=?", (user.user_name,))
    db_user = cursor.fetchone()
    conn.close()

    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")

    expire_time = datetime.utcnow() + timedelta(days=7)
    token_data = {"sub": db_user["user_id"], "name": db_user["user_name"], "exp": expire_time}
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": access_token, "token_type": "bearer"}

# ==========================================
# NHÓM 2: GIÁM SÁT THIẾT BỊ & MÔI TRƯỜNG
# ==========================================
@app.get("/api/status/environment", tags=["Live Status"])
def get_current_environment():
    """Lấy thông số Nhiệt độ và Ánh sáng mới nhất từ database"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value, timestamp FROM sensor_logs WHERE sensor_id='TEMP' ORDER BY timestamp DESC LIMIT 1")
    temp = cursor.fetchone()
    cursor.execute("SELECT value, timestamp FROM sensor_logs WHERE sensor_id='LIGHT' ORDER BY timestamp DESC LIMIT 1")
    light = cursor.fetchone()
    conn.close()
    return {"temperature": dict(temp) if temp else None, "light": dict(light) if light else None}
### UPDATE API CHO LOAD DANH SÁCH THIẾT BỊ (CÓ KÈM ID của thiết bị)
# Hiện có LED và FAN, sau này có thể có LED1 LED2 FAN1 FAN2 ....
@app.get("/api/status/devices", tags=["Live Status"])
def list_all_devices_status():
    """Lấy danh sách tất cả thiết bị thực tế kèm trạng thái mới nhất (Né các SET_)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
        SELECT d.device_id, d.description, 
               COALESCE((SELECT status FROM device_logs 
                         WHERE device_id = d.device_id 
                         ORDER BY timestamp DESC LIMIT 1), 0) as status
        FROM devices d 
        WHERE d.device_id NOT LIKE 'SET_%'
    """
    cursor.execute(query)
    devices = cursor.fetchall()
    conn.close()
    return {"data": [dict(row) for row in devices]}

# ==========================================
# NHÓM 3: ĐIỀU KHIỂN THIẾT BỊ ĐỘNG (MQTT)
# ==========================================
@app.post("/api/devices/{device_id}/control", tags=["Control"])
def control_device(device_id: str, command: DeviceControl):
    """Gửi lệnh điều khiển thiết bị thông qua giao thức MQTT"""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Kiểm tra thiết bị có tồn tại trong danh mục không
    cursor.execute("SELECT device_id FROM devices WHERE device_id = ? AND device_id NOT LIKE 'SET_%'", (device_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail=f"Thiết bị '{device_id}' không hợp lệ!")

    try:
        # 2. Publish lệnh qua MQTT (Ví dụ: device-fan, device-led)
        feed_name = f"device-{device_id.lower()}"
        mqtt.publish(feed_name, command.status)

        # 3. Lưu lịch sử thao tác từ App vào Database
        cursor.execute(
            "INSERT INTO device_logs (device_id, status, trigger_source) VALUES (?, ?, ?)",
            (device_id, command.status, command.trigger_source)
        )
        conn.commit()
        conn.close()
        return {"message": f"Đã gửi lệnh {command.status} tới {device_id} thành công!"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {str(e)}")

# ==========================================
# NHÓM 4: TRUY XUẤT NHẬT KÝ (LOGS)
# ==========================================
@app.get("/api/logs/cameras", tags=["Logs Dashboard"])
def get_camera_logs(limit: int = 10):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM camera_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    logs = cursor.fetchall()
    conn.close()
    return {"data": [dict(row) for row in logs]}

@app.get("/api/logs/sensors", tags=["Logs Dashboard"])
def get_sensor_logs(sensor_id: str = None, limit: int = 20):
    conn = get_db_connection()
    cursor = conn.cursor()
    if sensor_id:
        cursor.execute("SELECT * FROM sensor_logs WHERE sensor_id=? ORDER BY timestamp DESC LIMIT ?", (sensor_id, limit))
    else:
        cursor.execute("SELECT * FROM sensor_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    logs = cursor.fetchall()
    conn.close()
    return {"data": [dict(row) for row in logs]}