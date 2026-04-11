import os
import sys
import json
import uuid
from datetime import datetime, timedelta
from functools import wraps

import jwt
from fastapi import FastAPI, HTTPException, Depends, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Any

# Add parent directory to path for imports
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
sys.path.append(ROOT_DIR)

from database.db_manager import DatabaseManager
from modules.motion_detection.utils.logger import send_mqtt_command

load_dotenv()

# ==================== CONFIG ====================
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
EXPIRE_MINUTES = 60 * 24  # 24 hours

app = FastAPI(title="DADN Smart Home API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = DatabaseManager()

# Migrate database if needed (add missing columns for old databases)
db.migrate_database()

# ==================== MODELS ====================
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class DeviceCreate(BaseModel):
    name: str
    type: str  # "light" or "fan"
    roomId: str = "LIVING"

class DeviceUpdate(BaseModel):
    name: str = None
    state_json: str = None

class DeviceControl(BaseModel):
    command: str  # "toggle", "setSpeed", "setOscillation", "setTracking"
    value: Any = None  # can be bool, int, float

class RoomCreate(BaseModel):
    roomId: str
    name: str

class PresetCreate(BaseModel):
    id: str
    name: str
    icon: str = "⚙️"
    roomId: str = None
    deviceConfigs: dict = {}

class PresetUpdate(BaseModel):
    name: str = None
    icon: str = None
    roomId: str = None
    deviceConfigs: dict = None

class TokenData(BaseModel):
    user_id: int = None
    username: str = None

# ==================== AUTH HELPERS ====================
def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    payload = {"user_id": user_id, "username": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return TokenData(user_id=payload.get("user_id"), username=payload.get("username"))
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    else:
        token = authorization
    
    return verify_token(token)

# ==================== DEVICE MAPPING ====================
# Map mobile device types to Adafruit feeds
DEVICE_FEED_MAP = {
    "light-1": {"feed": "device-led", "type": "light"},
    "fan-1": {"feed": "device-fan", "type": "fan"},
}

def get_adafruit_feed(device_id: str, command: str = None):
    """Map device_id to Adafruit feed"""
    if device_id.startswith("light"):
        return "device-led"
    elif device_id.startswith("fan"):
        if command == "setSpeed":
            return "fan-speed-1"
        elif command == "setOscillation":
            return "oscillation-toggle"
        elif command == "setTracking":
            return "tracking-toggle"
        return "device-fan"
    return None

# ==================== AUTH ENDPOINTS ====================
@app.post("/api/auth/register")
def register(request: RegisterRequest):
    result = db.create_user(request.username, request.password)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    
    # Create default devices for new user
    user_id = result["user_id"]
    db.add_user_device(user_id, "light-1", "Đèn 1", "light", "LIVING")
    db.add_user_device(user_id, "fan-1", "Quạt 1", "fan", "LIVING")
    
    # Create default rooms for new user
    db.get_user_rooms(user_id)  # This will create 4 default rooms
    
    token = create_token(user_id, request.username)
    return {"token": token, "user_id": user_id, "username": request.username}

@app.post("/api/auth/login")
def login(request: LoginRequest):
    user = db.get_user(request.username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not db.verify_password(user["password"], request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token = create_token(user["id"], user["username"])
    return {"token": token, "user_id": user["id"], "username": user["username"]}

# ==================== USER AVATAR ENDPOINTS ====================
class AvatarUpdate(BaseModel):
    avatar: str  # Base64 encoded string

@app.post("/api/users/avatar")
def update_avatar(
    avatar_data: AvatarUpdate,
    authorization: str = Depends(get_current_user)
):
    success = db.update_user_avatar(authorization.user_id, avatar_data.avatar)
    return {"success": success}

@app.get("/api/users/avatar")
def get_avatar(authorization: str = Depends(get_current_user)):
    avatar = db.get_user_avatar(authorization.user_id)
    return {"avatar": avatar}

# ==================== DEVICE ENDPOINTS ====================
@app.get("/api/devices")
def get_devices(authorization: str = Depends(get_current_user)):
    devices = db.get_user_devices(authorization.user_id)
    return {"devices": devices}

@app.post("/api/devices")
def create_device(
    device: DeviceCreate,
    authorization: str = Depends(get_current_user)
):
    # Generate unique device_id
    device_id = f"{device.type}-{uuid.uuid4().hex[:6]}"
    
    db.add_user_device(
        user_id=authorization.user_id,
        device_id=device_id,
        name=device.name,
        device_type=device.type,
        room_id=device.roomId
    )
    
    db.log_device(device_id, 1, f"Tạo thiết bị {device.name}")
    
    return {"success": True, "device_id": device_id}

@app.put("/api/devices/{device_id}")
def update_device(
    device_id: str,
    updates: DeviceUpdate,
    authorization: str = Depends(get_current_user)
):
    update_dict = {}
    if updates.name:
        update_dict["name"] = updates.name
    if updates.state_json:
        update_dict["state_json"] = updates.state_json
    
    if update_dict:
        db.update_user_device(authorization.user_id, device_id, update_dict)
    
    return {"success": True}

@app.delete("/api/devices/{device_id}")
def delete_device(
    device_id: str,
    authorization: str = Depends(get_current_user)
):
    success = db.delete_user_device(authorization.user_id, device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"success": True}

@app.post("/api/devices/{device_id}/control")
def control_device(
    device_id: str,
    control: DeviceControl,
    authorization: str = Depends(get_current_user)
):
    # Get current device state
    devices = db.get_user_devices(authorization.user_id)
    device = next((d for d in devices if d["id"] == device_id), None)
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Get Adafruit feed
    feed = get_adafruit_feed(device_id, control.command)
    if not feed:
        raise HTTPException(status_code=400, detail="Unknown device type")
    
    # Determine value to send
    value = 1
    new_state = {}
    
    if control.command == "toggle":
        value = 0 if device.get("isOn", False) else 1
        new_state["isOn"] = bool(value)
    elif control.command == "setSpeed":
        value = int(control.value) if control.value else 1
        new_state["speed"] = value
    elif control.command == "setOscillation":
        value = 1 if control.value else 0
        new_state["isOscillating"] = bool(value)
    elif control.command == "setTracking":
        value = 1 if control.value else 0
        new_state["isTracking"] = bool(value)
    elif control.command == "setBrightness":
        value = int(control.value) if control.value else 50
        new_state["brightness"] = value
    
    # Send to Adafruit IO
    try:
        send_mqtt_command_to_feed(feed, value)
    except Exception as e:
        print(f"MQTT Error: {e}")
    
    # Update device state in database
    current_state = device.copy()
    current_state.update(new_state)
    db.update_user_device(
        authorization.user_id,
        device_id,
        {"state_json": json.dumps(current_state)}
    )
    
    status_int = 1 if new_state.get("isOn", False) else 0
    db.log_device(device_id, status_int, f"Điều khiển {control.command}")
    
    return {"success": True, "message": f"Device {control.command} executed", "value": value}

def send_mqtt_command_to_feed(feed_key: str, value: int):
    """Send command to Adafruit IO"""
    try:
        from Adafruit_IO import MQTTClient
        from dotenv import load_dotenv
        load_dotenv()
        
        AIO_USERNAME = os.getenv("AIO_USERNAME")
        AIO_KEY = os.getenv("AIO_KEY")
        
        client = MQTTClient(AIO_USERNAME, AIO_KEY)
        client.connect()
        client.publish(feed_key, value)
        print(f"[API] Sent {value} to feed {feed_key}")
    except Exception as e:
        print(f"[API] MQTT Error: {e}")

# ==================== ROOM ENDPOINTS ====================
@app.get("/api/rooms")
def get_rooms(authorization: str = Depends(get_current_user)):
    rooms = db.get_user_rooms(authorization.user_id)
    return {"rooms": rooms}

@app.post("/api/rooms")
def create_room(
    room: RoomCreate,
    authorization: str = Depends(get_current_user)
):
    db.add_user_room(authorization.user_id, room.roomId, room.name)
    return {"success": True}

@app.delete("/api/rooms/{room_id}")
def delete_room(
    room_id: str,
    authorization: str = Depends(get_current_user)
):
    success = db.delete_user_room(authorization.user_id, room_id)
    if not success:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"success": True}

# ==================== PRESET ENDPOINTS ====================
@app.get("/api/presets")
def get_presets(authorization: str = Depends(get_current_user)):
    print(f"[API] get_presets: user_id={authorization.user_id}")
    presets = db.get_user_presets(authorization.user_id)
    print(f"[API] Returning {len(presets)} presets")
    return {"presets": presets}

@app.post("/api/presets")
def create_preset(
    preset: PresetCreate,
    authorization: str = Depends(get_current_user)
):
    print(f"[API] create_preset: user_id={authorization.user_id}, preset_id={preset.id}, name={preset.name}")
    device_configs_json = json.dumps(preset.deviceConfigs) if preset.deviceConfigs else "{}"
    
    db.add_user_preset(
        user_id=authorization.user_id,
        preset_id=preset.id,
        name=preset.name,
        icon=preset.icon,
        room_id=preset.roomId,
        device_configs_json=device_configs_json
    )
    
    return {"success": True, "message": f"Preset {preset.name} created"}

@app.put("/api/presets/{preset_id}")
def update_preset(
    preset_id: str,
    updates: PresetUpdate,
    authorization: str = Depends(get_current_user)
):
    update_dict = {}
    if updates.name:
        update_dict["name"] = updates.name
    if updates.icon:
        update_dict["icon"] = updates.icon
    if updates.roomId:
        update_dict["room_id"] = updates.roomId
    if updates.deviceConfigs:
        update_dict["device_configs_json"] = json.dumps(updates.deviceConfigs)
    
    if update_dict:
        db.update_user_preset(authorization.user_id, preset_id, **update_dict)
    
    return {"success": True}

@app.delete("/api/presets/{preset_id}")
def delete_preset(
    preset_id: str,
    authorization: str = Depends(get_current_user)
):
    success = db.delete_user_preset(authorization.user_id, preset_id)
    if not success:
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"success": True}

# ==================== STATUS ENDPOINTS ====================
@app.get("/api/status")
def get_status():
    """Get sensor status from Adafruit IO"""
    # This would normally fetch from Adafruit IO
    # For now, return mock data
    return {
        "temperature": 28,
        "light": 150,
        "pir": False,
        "human_detect": False
    }

# ==================== RUN ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
