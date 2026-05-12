from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Any, Optional, Dict
import sqlite3
import json
import uuid
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
ALGORITHM = os.getenv("ALGORITHM", "HS256")

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
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class DeviceControl(BaseModel):
    command: str       # "isOn", "brightness", "speed", "isOscillating", "isTracking", "color"
    value: Any = None  # bool / int / -256...

# ==========================================
# 5. HÀM HỖ TRỢ KẾT NỐI DATABASE & JWT DEPENDENCY
# ==========================================
def get_db_connection():
    conn = sqlite3.connect("smart_home.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
    """Đọc JWT từ header Authorization: Bearer <token>, trả về user_id."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
        return int(user_id)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token đã hết hạn")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")

# ==========================================
# NHÓM 1: XÁC THỰC TÀI KHOẢN (AUTH)
# ==========================================
@app.post("/api/auth/register", tags=["Authentication"])
def register_user(user: UserRegister):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (user.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Username đã tồn tại!")
    
    hashed_password = pwd_context.hash(user.password)
    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                   (user.username, hashed_password))
    conn.commit()
    user_id = cursor.lastrowid
    conn.close()

    expire_time = datetime.utcnow() + timedelta(days=7)
    token_data = {"sub": str(user_id), "name": user.username, "exp": expire_time}
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    
    return {"token": access_token, "user_id": user_id, "username": user.username}

@app.post("/api/auth/login", tags=["Authentication"])
def login_user(user: UserLogin):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (user.username,))
    db_user = cursor.fetchone()
    conn.close()

    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu!")

    expire_time = datetime.utcnow() + timedelta(days=7)
    token_data = {"sub": str(db_user["id"]), "name": db_user["username"], "exp": expire_time}
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": access_token, "user_id": db_user["id"], "username": db_user["username"]}

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
# NHÓM 3: ĐIỀU KHIỂN USER DEVICE (cập nhật state_json + MQTT)
# ==========================================
@app.post("/api/devices/{device_id}/control", tags=["Control"])
def control_device(
    device_id: str,
    command: DeviceControl,
    user_id: int = Depends(get_current_user_id),
):
    """Cập nhật state_json của user_device theo {command, value}.
    Với type=light/fan và command=isOn, đồng thời publish MQTT để bật/tắt phần cứng."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT type, state_json FROM user_devices WHERE user_id = ? AND device_id = ?",
        (user_id, device_id),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Thiết bị '{device_id}' không tồn tại")

    device_type = row["type"]
    state = json.loads(row["state_json"]) if row["state_json"] else {}
    state[command.command] = command.value
    new_state_json = json.dumps(state)

    cursor.execute(
        "UPDATE user_devices SET state_json = ? WHERE user_id = ? AND device_id = ?",
        (new_state_json, user_id, device_id),
    )
    conn.commit()
    conn.close()

    print(f"[CONTROL] user={user_id} device={device_id} type={device_type} "
          f"{command.command}={command.value}")

    if command.command == "isOn":
        mqtt_value = 1 if command.value else 0
        try:
            if device_type == "light":
                mqtt.publish("device-led", mqtt_value)
                cursor_log = get_db_connection()
                cursor_log.execute(
                    "INSERT INTO device_logs (device_id, status, trigger_source) VALUES (?, ?, ?)",
                    ("LED", mqtt_value, f"App_User_{user_id}"),
                )
                cursor_log.commit()
                cursor_log.close()
            elif device_type == "fan":
                mqtt.publish("device-fan", mqtt_value)
                cursor_log = get_db_connection()
                cursor_log.execute(
                    "INSERT INTO device_logs (device_id, status, trigger_source) VALUES (?, ?, ?)",
                    ("FAN", mqtt_value, f"App_User_{user_id}"),
                )
                cursor_log.commit()
                cursor_log.close()
        except Exception as e:
            print(f"[CONTROL] MQTT publish error: {e}")

    return {"success": True, "message": f"Đã cập nhật {command.command}={command.value}"}

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

# ==========================================
# NHÓM 6: MODELS (USER CRUD)
# ==========================================
class DeviceCreate(BaseModel):
    name: str
    type: str
    roomId: str

class AvatarUpdate(BaseModel):
    avatar: str

class RoomCreate(BaseModel):
    roomId: str
    name: str

class PresetCreate(BaseModel):
    id: str
    name: str
    icon: str
    roomId: Optional[str] = None
    deviceConfigs: Dict[str, Any] = {}

class PresetUpdate(BaseModel):
    name: Optional[str] = None
    icon: Optional[str] = None
    roomId: Optional[str] = None
    deviceConfigs: Optional[Dict[str, Any]] = None

# ==========================================
# NHÓM 7: USER DEVICES (CRUD)
# ==========================================
@app.get("/api/devices", tags=["User Devices"])
def list_user_devices(user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT device_id, name, type, room_id, state_json FROM user_devices WHERE user_id = ?",
        (user_id,)
    )
    devices = []
    for row in cursor.fetchall():
        state = json.loads(row["state_json"]) if row["state_json"] else {}
        devices.append({
            "id": row["device_id"],
            "name": row["name"],
            "type": row["type"],
            "roomId": row["room_id"],
            **state
        })
    conn.close()
    return {"devices": devices}

@app.post("/api/devices", tags=["User Devices"])
def create_user_device(req: DeviceCreate, user_id: int = Depends(get_current_user_id)):
    device_id = uuid.uuid4().hex
    if req.type == "light":
        state_json = json.dumps({"isOn": False, "brightness": 50, "color": -256})
    else:
        state_json = json.dumps({"isOn": False, "speed": 1, "isOscillating": False, "isTracking": False})

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_devices (user_id, device_id, name, type, room_id, state_json) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, device_id, req.name, req.type, req.roomId, state_json)
    )
    conn.commit()
    conn.close()
    return {"success": True, "device_id": device_id}

@app.delete("/api/devices/{device_id}", tags=["User Devices"])
def delete_user_device_endpoint(device_id: str, user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_devices WHERE user_id = ? AND device_id = ?",
        (user_id, device_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return {"success": deleted}

# ==========================================
# NHÓM 8: USER ROOMS
# ==========================================
def _ensure_default_rooms(cursor, user_id: int):
    """Tạo 4 phòng mặc định nếu user chưa có phòng nào."""
    cursor.execute("SELECT COUNT(*) FROM user_rooms WHERE user_id = ?", (user_id,))
    if cursor.fetchone()[0] == 0:
        defaults = [
            ("LIVING", "Phòng khách"),
            ("BED", "Phòng ngủ"),
            ("KITCHEN", "Nhà bếp"),
            ("GARDEN", "Sân vườn"),
        ]
        for room_id, name in defaults:
            cursor.execute(
                "INSERT INTO user_rooms (user_id, room_id, name) VALUES (?, ?, ?)",
                (user_id, room_id, name)
            )

@app.get("/api/rooms", tags=["User Rooms"])
def list_user_rooms(user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _ensure_default_rooms(cursor, user_id)
    cursor.execute("SELECT room_id, name FROM user_rooms WHERE user_id = ?", (user_id,))
    rooms = [{"id": row["room_id"], "name": row["name"]} for row in cursor.fetchall()]
    conn.commit()
    conn.close()
    return {"rooms": rooms}

@app.post("/api/rooms", tags=["User Rooms"])
def create_user_room(req: RoomCreate, user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_rooms (user_id, room_id, name) VALUES (?, ?, ?)",
        (user_id, req.roomId, req.name)
    )
    conn.commit()
    conn.close()
    return {"success": True}

@app.delete("/api/rooms/{room_id}", tags=["User Rooms"])
def delete_user_room_endpoint(room_id: str, user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_devices WHERE user_id = ? AND room_id = ?",
        (user_id, room_id)
    )
    cursor.execute(
        "DELETE FROM user_presets WHERE user_id = ? AND room_id = ?",
        (user_id, room_id)
    )
    cursor.execute(
        "DELETE FROM user_rooms WHERE user_id = ? AND room_id = ?",
        (user_id, room_id)
    )
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return {"success": deleted}

# ==========================================
# NHÓM 9: USER AVATAR
# ==========================================
@app.post("/api/users/avatar", tags=["User"])
def update_avatar(req: AvatarUpdate, user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET avatar = ? WHERE id = ?", (req.avatar, user_id))
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return {"success": updated, "avatar": req.avatar if updated else None}

@app.get("/api/users/avatar", tags=["User"])
def get_avatar(user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT avatar FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    avatar = row["avatar"] if row else None
    return {"success": avatar is not None, "avatar": avatar}

# ==========================================
# NHÓM 10: USER PRESETS
# ==========================================
@app.get("/api/presets", tags=["User Presets"])
def list_presets(user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT preset_id, name, icon, room_id, device_configs_json FROM user_presets WHERE user_id = ?",
        (user_id,)
    )
    presets = []
    for row in cursor.fetchall():
        configs = json.loads(row["device_configs_json"]) if row["device_configs_json"] else {}
        presets.append({
            "id": row["preset_id"],
            "name": row["name"],
            "icon": row["icon"],
            "roomId": row["room_id"],
            "deviceConfigs": configs
        })
    conn.close()
    return {"presets": presets}

@app.post("/api/presets", tags=["User Presets"])
def create_preset(req: PresetCreate, user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO user_presets (user_id, preset_id, name, icon, room_id, device_configs_json) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, req.id, req.name, req.icon, req.roomId, json.dumps(req.deviceConfigs))
    )
    conn.commit()
    conn.close()
    return {"success": True}

@app.put("/api/presets/{preset_id}", tags=["User Presets"])
def update_preset_endpoint(
    preset_id: str,
    req: PresetUpdate,
    user_id: int = Depends(get_current_user_id)
):
    updates = {}
    if req.name is not None:
        updates["name"] = req.name
    if req.icon is not None:
        updates["icon"] = req.icon
    if req.roomId is not None:
        updates["room_id"] = req.roomId
    if req.deviceConfigs is not None:
        updates["device_configs_json"] = json.dumps(req.deviceConfigs)

    if not updates:
        return {"success": False}

    set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [user_id, preset_id]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE user_presets SET {set_clause} WHERE user_id = ? AND preset_id = ?",
        values
    )
    conn.commit()
    updated = cursor.rowcount > 0
    conn.close()
    return {"success": updated}

@app.delete("/api/presets/{preset_id}", tags=["User Presets"])
def delete_preset_endpoint(preset_id: str, user_id: int = Depends(get_current_user_id)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_presets WHERE user_id = ? AND preset_id = ?",
        (user_id, preset_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return {"success": deleted}

# ==========================================
# NHÓM 11: SNAPSHOT STATUS (cho mobile)
# ==========================================
@app.get("/api/status", tags=["Live Status"])
def get_status_snapshot(user_id: int = Depends(get_current_user_id)):
    """Trả về temperature, light, pir, human_detect ở dạng phẳng cho mobile."""
    conn = get_db_connection()
    cursor = conn.cursor()

    def latest(sensor_id):
        cursor.execute(
            "SELECT value FROM sensor_logs WHERE sensor_id=? ORDER BY timestamp DESC LIMIT 1",
            (sensor_id,)
        )
        r = cursor.fetchone()
        return r["value"] if r else None

    temp = latest("TEMP")
    light = latest("LIGHT")
    pir = latest("PIR")

    cursor.execute("SELECT has_human FROM camera_logs ORDER BY timestamp DESC LIMIT 1")
    cam = cursor.fetchone()
    human = bool(cam["has_human"]) if cam else False

    conn.close()
    return {
        "temperature": float(temp) if temp is not None else 0.0,
        "light": int(light) if light is not None else 0,
        "pir": bool(pir) if pir is not None else False,
        "human_detect": human
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)