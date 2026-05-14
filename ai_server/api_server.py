from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Any, Optional, Dict
import json
import uuid
import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()
# ==========================================
# 1. CẤU HÌNH SMART MQTT (Giao thức lõi)
# ==========================================
from mqtt_client import SmartHomeMQTT

print("[API SERVER] Đang khởi tạo kết nối MQTT ngầm...")
mqtt = SmartHomeMQTT()
mqtt.start()

# TẠO INSTANCE DUY NHẤT CỦA DATABASE (CÓ RLOCK)
from database.db_manager import DatabaseManager
db = DatabaseManager("smart_home.db")
print("[API SERVER] DB initialized — tables ready & Lock engaged.")

# =========================================
# 2. CẤU HÌNH BẢO MẬT & JWT TOKEN
# ==========================================
SECRET_KEY = os.getenv("SECRET_KEY", "your_super_secret_key_here")
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
    command: str
    value: Any = None

class DeviceCreate(BaseModel):
    device_id: str # thêm dòng để Mobile biết
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
# 5. JWT DEPENDENCY
# ==========================================
security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> int:
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
    result = db.create_user(user.username, user.password)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    user_id = result["user_id"]
    expire_time = datetime.utcnow() + timedelta(days=7)
    token_data = {"sub": str(user_id), "name": user.username, "exp": expire_time}
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return {"token": access_token, "user_id": user_id, "username": user.username}

@app.post("/api/auth/login", tags=["Authentication"])
def login_user(user: UserLogin):
    db_user = db.get_user(user.username)

    if not db_user or not db.verify_password(db_user["password"], user.password):
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
    return db.get_latest_environment()

@app.get("/api/status/devices", tags=["Live Status"])
def list_all_devices_status(user_id: int = Depends(get_current_user_id)):
    return {"data": db.get_all_devices_status(user_id)}

# ==========================================
# NHÓM 3: ĐIỀU KHIỂN USER DEVICE (cập nhật state_json + MQTT)
# ==========================================
@app.post("/api/devices/{device_id}/control", tags=["Control"])
def control_device(
    device_id: str,
    command: DeviceControl,
    user_id: int = Depends(get_current_user_id),
):
    row = db.get_user_device_by_id(user_id, device_id)
    if not row:
        raise HTTPException(status_code=404, detail=f"Thiết bị '{device_id}' không tồn tại")

    device_type = row["type"]
    state = json.loads(row["state_json"]) if row["state_json"] else {}
    
    # Vì Mobile đã gửi đúng key (ví dụ: speed, brightness), ta lưu thẳng vào DB luôn
    state[command.command] = command.value
    db.update_user_device_state(user_id, device_id, json.dumps(state))
    # THỐNG NHẤT TÊN FEED LIÊN QUAN DEVICE SẼ NHƯ SAU
    # device-<ID của device>
    # Dạng thông tin gửi đi sẽ là isOn:speed:isOsc:isTracking
    # Tức là nén thông tin của 1 device quạt lại, này bên Yolo sẽ dùng quy luật để parse lấy thoogn tin từng cái
    # với led sẽ có isOn:brightness:r:g:b
    
    # Đóng gói lại
    packed_data = ""
    if device_type == "fan":
        is_on = 1 if state.get("isOn") else 0
        speed = int(state.get("speed", 50)) # speed thì từ 0 - 100 (%) nên để mặc định 0 cho tắt
        is_osc = 1 if state.get("isOscillating") else 0
        is_track = 1 if state.get("isTracking") else 0
        # ép speed có 3 chữ số (ví dụ 36 là thành 036)
        packed_data = f"{is_on}:{speed:03d}:{is_osc}:{is_track}"
    elif device_type == "light":
        is_on = 1 if state.get("isOn") else 0
        brightness = int(state.get("brightness", 50))
        # Lấy giá trị màu (Int) từ Kotlin, này ko rành, tra gg thì bảo 1 số đại diện rồi mask ra lấy r g b hả ?
        color = int(state.get("color", -1))
        # Mổ xẻ màu Int thành 3 số thập phân R, G, B
        # Mask 0xFFFFFF để bỏ qua phần Alpha (độ trong suốt)
        rgb = color & 0xFFFFFF 
        r = (rgb >> 16) & 0xFF
        g = (rgb >> 8) & 0xFF
        b = rgb & 0xFF
        # Dùng :03d để ép luôn thành 3 chữ số (50 thành 050)
        packed_data = f"{is_on}:{brightness:03d}:{r:03d}:{g:03d}:{b:03d}"
    else: pass # chỗ này để mở rộng sau này, nếu mình có thêm loajit device khác
    
    device_feed_name = f"device-{device_id.lower()}"

    # Xử lí bắn MQTT lên cloud Ada
    try:
        mqtt.publish(device_feed_name, packed_data)

        if command.command == "isOn":
            mqtt_value = 1 if command.value else 0
            db.log_device(device_id, mqtt_value, f"App_User_{user_id}")
        
        print(f"[CONTROL] Đã gửi chuỗi '{packed_data}' lên feed '{device_feed_name}'")
    except Exception as e:
        print(f"[CONTROL] MQTT Error: {e}")

    return {"success": True, "message": f"Executed {command.command}"}

# ==========================================
# NHÓM 4: TRUY XUẤT NHẬT KÝ (LOGS)
# ==========================================
@app.get("/api/logs/cameras", tags=["Logs Dashboard"])
def get_camera_logs(limit: int = 10):
    return {"data": db.get_camera_logs(limit)}

@app.get("/api/logs/sensors", tags=["Logs Dashboard"])
def get_sensor_logs(sensor_id: str = None, limit: int = 20):
    return {"data": db.get_sensor_logs(sensor_id, limit)}

# ==========================================
# NHÓM 7: USER DEVICES (CRUD)
# ==========================================
@app.get("/api/devices", tags=["User Devices"])
def list_user_devices(user_id: int = Depends(get_current_user_id)):
    return {"devices": db.get_user_devices(user_id)}

@app.post("/api/devices", tags=["User Devices"])
def create_user_device(req: DeviceCreate, user_id: int = Depends(get_current_user_id)):
    device_id = req.device_id
    db.add_user_device(user_id, device_id, req.name, req.type, req.roomId)
    return {"success": True, "device_id": device_id}

@app.delete("/api/devices/{device_id}", tags=["User Devices"])
def delete_user_device_endpoint(device_id: str, user_id: int = Depends(get_current_user_id)):
    deleted = db.delete_user_device(user_id, device_id)
    return {"success": deleted}

# ==========================================
# NHÓM 8: USER ROOMS
# ==========================================
@app.get("/api/rooms", tags=["User Rooms"])
def list_user_rooms(user_id: int = Depends(get_current_user_id)):
    return {"rooms": db.get_user_rooms(user_id)}

@app.post("/api/rooms", tags=["User Rooms"])
def create_user_room(req: RoomCreate, user_id: int = Depends(get_current_user_id)):
    db.add_user_room(user_id, req.roomId, req.name)
    return {"success": True}

@app.delete("/api/rooms/{room_id}", tags=["User Rooms"])
def delete_user_room_endpoint(room_id: str, user_id: int = Depends(get_current_user_id)):
    deleted = db.delete_room_cascade(user_id, room_id)
    return {"success": deleted}

# ==========================================
# NHÓM 9: USER AVATAR
# ==========================================
@app.post("/api/users/avatar", tags=["User"])
def update_avatar(req: AvatarUpdate, user_id: int = Depends(get_current_user_id)):
    updated = db.update_user_avatar(user_id, req.avatar)
    return {"success": updated, "avatar": req.avatar if updated else None}

@app.get("/api/users/avatar", tags=["User"])
def get_avatar(user_id: int = Depends(get_current_user_id)):
    avatar = db.get_user_avatar(user_id)
    return {"success": avatar is not None, "avatar": avatar}

# ==========================================
# NHÓM 10: USER PRESETS
# ==========================================
@app.get("/api/presets", tags=["User Presets"])
def list_presets(user_id: int = Depends(get_current_user_id)):
    return {"presets": db.get_user_presets(user_id)}

@app.post("/api/presets", tags=["User Presets"])
def create_preset(req: PresetCreate, user_id: int = Depends(get_current_user_id)):
    db.add_user_preset(user_id, req.id, req.name, req.icon, req.roomId, json.dumps(req.deviceConfigs))
    return {"success": True}

@app.put("/api/presets/{preset_id}", tags=["User Presets"])
def update_preset_endpoint(preset_id: str, req: PresetUpdate, user_id: int = Depends(get_current_user_id)):
    updated = db.update_user_preset(
        user_id, preset_id, 
        name=req.name, icon=req.icon, room_id=req.roomId, 
        device_configs_json=json.dumps(req.deviceConfigs) if req.deviceConfigs else None
    )
    return {"success": updated}

@app.delete("/api/presets/{preset_id}", tags=["User Presets"])
def delete_preset_endpoint(preset_id: str, user_id: int = Depends(get_current_user_id)):
    deleted = db.delete_user_preset(user_id, preset_id)
    return {"success": deleted}

# ==========================================
# NHÓM 11: SNAPSHOT STATUS (cho mobile)
# ==========================================
@app.get("/api/status", tags=["Live Status"])
def get_status_snapshot(user_id: int = Depends(get_current_user_id)):
    return db.get_snapshot_status()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)