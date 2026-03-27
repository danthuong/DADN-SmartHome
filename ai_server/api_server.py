from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
from Adafruit_IO import Client
import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

# ==========================================
# CẤU HÌNH ADAFRUIT IO (Gửi lệnh Control)
# ==========================================
AIO_USERNAME = "thinhphan2313306"
AIO_KEY = "aio_VWuR71QDMpqjdnUvo65mq4sZKtmI"
aio = Client(AIO_USERNAME, AIO_KEY)

# =========================================
# CẤU HÌNH BẢO MẬT & JWT TOKEN
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "khoa_bi_mat_cua_nhom_iot"  # Khóa dùng để ký xác nhận Token
ALGORITHM = "HS256"

# ==========================================
# KHỞI TẠO FASTAPI SERVER
# ==========================================
app = FastAPI(
    title="Smart Home API",
    description="Hệ thống API điều khiển và giám sát nhà thông minh có xác thực",
    version="1.0.0"
)

# ==========================================
# MODELS (Khuôn mẫu dữ liệu nhận từ App)
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

class ThresholdSetting(BaseModel):
    temp: float
    light: float

# ==========================================
# 5. HÀM HỖ TRỢ KẾT NỐI DATABASE
# ==========================================
def get_db_connection():
    conn = sqlite3.connect("smart_home.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row  # Trả về Dictionary (JSON) thay vì Tuple
    return conn

# ==========================================
# NHÓM API 1: XÁC THỰC TÀI KHOẢN (AUTH)
# ==========================================
@app.post("/api/auth/register", tags=["Authentication"])
def register_user(user: UserRegister):
    """Đăng ký tài khoản mới"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM accounts WHERE user_id=? OR user_name=?", (user.user_id, user.user_name))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="User ID hoặc Username đã tồn tại!")

    # Băm mật khẩu để bảo mật
    hashed_password = pwd_context.hash(user.password)

    cursor.execute(
        "INSERT INTO accounts (user_id, user_name, password) VALUES (?, ?, ?)",
        (user.user_id, user.user_name, hashed_password)
    )
    conn.commit()
    conn.close()
    
    return {"message": f"Đăng ký thành công tài khoản: {user.user_name}"}

@app.post("/api/auth/login", tags=["Authentication"])
def login_user(user: UserLogin):
    """Đăng nhập để nhận chuỗi Token sử dụng App"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM accounts WHERE user_name=?", (user.user_name,))
    db_user = cursor.fetchone()
    conn.close()

    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")

    # Tạo thẻ thông hành (Token) hạn 7 ngày
    expire_time = datetime.utcnow() + timedelta(days=7)
    token_data = {
        "sub": db_user["user_id"],
        "name": db_user["user_name"],
        "exp": expire_time
    }
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)

    return {
        "message": "Đăng nhập thành công!",
        "access_token": access_token,
        "token_type": "bearer"
    }

# ==========================================
# NHÓM API 2: TRẠNG THÁI HIỆN TẠI (LIVE STATUS)
# ==========================================
@app.get("/api/status/environment", tags=["Live Status"])
def get_current_environment():
    """Lấy thông số Nhiệt độ và Ánh sáng mới nhất"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT value, timestamp FROM sensor_logs WHERE sensor_id='TEMP' ORDER BY timestamp DESC LIMIT 1")
    temp_data = cursor.fetchone()
    # lấy dòng cuối (trạng thái mới nhất của nhiệt và độ sáng)
    cursor.execute("SELECT value, timestamp FROM sensor_logs WHERE sensor_id='LIGHT' ORDER BY timestamp DESC LIMIT 1")
    light_data = cursor.fetchone()
    conn.close()

    return {
        "temperature": dict(temp_data) if temp_data else None,
        "light": dict(light_data) if light_data else None
    }

@app.get("/api/status/devices", tags=["Live Status"])
def get_current_devices():
    """Xem Quạt và Đèn hiện tại đang Bật hay Tắt"""
    conn = get_db_connection()
    cursor = conn.cursor()
    # lấy dòng cuối (trạng thái mới nhất của đèn và quạt)
    cursor.execute("SELECT status, trigger_source, timestamp FROM device_logs WHERE device_id='FAN' ORDER BY timestamp DESC LIMIT 1")
    fan_data = cursor.fetchone()
    
    cursor.execute("SELECT status, trigger_source, timestamp FROM device_logs WHERE device_id='LED' ORDER BY timestamp DESC LIMIT 1")
    led_data = cursor.fetchone()
    conn.close()

    return {
        "FAN": dict(fan_data) if fan_data else {"status": 0},
        "LED": dict(led_data) if led_data else {"status": 0}
    }

# ==========================================
# NHÓM API 3: ĐIỀU KHIỂN THIẾT BỊ (CONTROL)
# ==========================================
@app.post("/api/devices/{device_id}/control", tags=["Control"])
def control_device(device_id: str, command: DeviceControl):
    """Gửi lệnh Bật/Tắt thiết bị (FAN hoặc LED)"""
    if device_id not in ["FAN", "LED"]:
        raise HTTPException(status_code=400, detail="Mã thiết bị không hợp lệ (Chỉ nhận FAN hoặc LED)")

    try:
        # 1. Bắn lệnh lên Cloud Adafruit IO
        feed_name = "device-fan" if device_id == "FAN" else "device-led"
        aio.send_data(feed_name, command.status)

        # 2. Lưu lịch sử vào Database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO device_logs (device_id, status, trigger_source) VALUES (?, ?, ?)",
            (device_id, command.status, command.trigger_source)
        )
        conn.commit()
        conn.close()

        return {"message": f"Đã gửi lệnh {'BẬT' if command.status == 1 else 'TẮT'} cho {device_id} thành công!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi gửi lệnh: {str(e)}")

# ==========================================
# NHÓM API 4: LỊCH SỬ HỆ THỐNG (LOGS DASHBOARD)
# ==========================================
@app.get("/api/logs/cameras", tags=["Logs Dashboard"])
def get_camera_logs(limit: int = 10):
    """Lấy danh sách các lần phát hiện người/khuôn mặt"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM camera_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    logs = cursor.fetchall()
    conn.close()
    return {"data": [dict(row) for row in logs]}

@app.get("/api/logs/devices", tags=["Logs Dashboard"])
def get_device_logs(limit: int = 20):
    """Lấy lịch sử bật tắt thiết bị và lý do"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM device_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    logs = cursor.fetchall()
    conn.close()
    return {"data": [dict(row) for row in logs]}

@app.get("/api/logs/sensors", tags=["Logs Dashboard"])
def get_sensor_logs(sensor_id: str = None, limit: int = 20):
    """Lấy lịch sử cảm biến (Có thể truyền ?sensor_id=TEMP để lọc)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if sensor_id:
        cursor.execute("SELECT * FROM sensor_logs WHERE sensor_id=? ORDER BY timestamp DESC LIMIT ?", (sensor_id, limit))
    else:
        cursor.execute("SELECT * FROM sensor_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        
    logs = cursor.fetchall()
    conn.close()
    return {"data": [dict(row) for row in logs]}