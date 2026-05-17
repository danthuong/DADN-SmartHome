import time
import sys
import json
from mqtt_client import SmartHomeMQTT
from database.db_manager import DatabaseManager 

db = DatabaseManager()

# ==========================================
# ĐỊNH NGHĨA CÁC HÀM LẮNG NGHE CHO THƯ KÝ
# ==========================================

def thuky_on_connect(client):
    print("\n[LOGGER] Đã kết nối Đám mây. Chỉ lắng nghe những giá trị mà cảm biến ghi nhận hoặc server AI")
    
    # Đăng ký nghe ngóng CẢM BIẾN & AI
    client.subscribe("human-detect-pir") 
    client.subscribe("env-temp") 
    client.subscribe("env-light") 
    client.subscribe("human-detect-ai")
    
    # Nếu sau này có FaceID hay Cử chỉ thì cứ thêm vào đây:
    # client.subscribe("host-detect")
    client.subscribe("gesture-log")

def thuky_on_message(client, feed_id, payload):
    try:
        # XỬ LÝ DỮ LIỆU LÀ CHỮ (Lệnh cử chỉ từ AI)
        # Do lúc demo Yolo bit chỉ có 1 đèn 1 quạt (2 cái này tạm sẽ ứng với id là "LED" và "FAN" luôn)
        # Mở rộng sau này khi vào thwucj tế ta sẽ thiết lập camera id điều khiển device id tương ứng...
        if feed_id == "gesture-log":
            gesture_cmd = str(payload)
            db.log_gesture(camera_id="CAM_01", gesture_name=gesture_cmd)
            print(f"[{time.strftime('%H:%M:%S')}] [AI GESTURE] Phát hiện cử chỉ: {gesture_cmd}")
            # Xử lí Clapping - Bật tắt đèn
            if gesture_cmd == "Clapping":
                device_id = "LED"
                row = db.get_shared_device_state(device_id)
                if row:
                    state = json.loads(row["state_json"]) if row["state_json"] else {}
                    new_on_state = not state.get("isOn", False)
                    state["isOn"] = new_on_state
                    db.update_shared_device_state(device_id, json.dumps(state))
                    # Đóng gói cho LED (isOn:brightness:R:G:B)
                    is_on = 1 if new_on_state else 0
                    br = int(state.get("brightness", 50))
                    color = int(state.get("color", 16777215)) # Trắng mặc định
                    rgb = color & 0xFFFFFF
                    r, g, b = (rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF
                    
                    packed_data = f"{is_on}:{br:03d}:{r:03d}:{g:03d}:{b:03d}"
                    mqtt.publish("device-led", packed_data)
            # Xử lí các cử chỉ liên quan đến quạt
            elif gesture_cmd in ["Close palm", "One", "Two", "Three", "Victory", "Shaking"]:
                device_id = "FAN"
                row = db.get_shared_device_state(device_id)
                if row:
                    state = json.loads(row["state_json"]) if row["state_json"] else {}
                    if gesture_cmd == "Close palm": # bật tắt quạt
                        state["isOn"] = not state.get("isOn", False)
                    # tốc độ 
                    elif gesture_cmd == "One": state["speed"] = 33
                    elif gesture_cmd == "Two": state["speed"] = 66
                    elif gesture_cmd == "Three": state["speed"] = 100
                    elif gesture_cmd == "Victory": # Chữ V -> bật tắt Tracking
                        state["isTracking"] = not state.get("isTracking", False)
                    elif gesture_cmd == "Shaking": # Lắc tay -> bật tắt Oscillation
                        state["isOscillating"] = not state.get("isOscillating", False)
                    db.update_shared_device_state(device_id, json.dumps(state))
                    # Đóng gói cho FAN (isOn:speed:isOsc:isTracking)
                    is_on = 1 if state.get("isOn") else 0
                    speed = int(state.get("speed", 50))
                    is_osc = 1 if state.get("isOscillating") else 0
                    is_track = 1 if state.get("isTracking") else 0
                    
                    packed_data = f"{is_on}:{speed:03d}:{is_osc}:{is_track}"
                    mqtt.publish("device-fan", packed_data)
                    print(f"   -> Đã update QUẠT thành: {packed_data}")
        else:
            val = float(payload) 
            
            if feed_id == "human-detect-pir":
                db.log_sensor("PIR", val)
                print(f"[{time.strftime('%H:%M:%S')}] Log: PIR = {val}")
                
            elif feed_id == "env-temp":
                db.log_sensor("TEMP", val)
                
            elif feed_id == "env-light":
                db.log_sensor("LIGHT", val)
                
            elif feed_id == "human-detect-ai":
                db.log_camera(camera_id="CAM_01", has_human=val) # Chú ý tên CAM_01 cho khớp DB Master data
                print(f"[{time.strftime('%H:%M:%S')}] Log: AI Camera = {val}")
        
            
    except Exception as e:
        print(f"[CẢNH BÁO] Lỗi ghi chép dữ liệu từ kênh {feed_id}: {e}")

# ==========================================
# KHỞI ĐỘNG DỊCH VỤ GHI CHÉP
# ==========================================

print("=======================================")
print("   KÍCH HOẠT DATABASE LOGGER SERVICE   ")
print("=======================================")

# Khởi tạo MQTT
mqtt = SmartHomeMQTT()

# Ép client dùng 2 hàm nghe của riêng file Logger này
mqtt.setup_subscriber(custom_on_connect=thuky_on_connect, custom_on_message=thuky_on_message)

mqtt.start()

# vòng lặp duy trì việc lắng nghe và ghi log
try:
    while True:
        time.sleep(1) 
except KeyboardInterrupt:
    print("\n[LOGGER] Đã tắt Log Service!")
    sys.exit(0)