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
        # 2. XỬ LÝ DỮ LIỆU LÀ CHỮ (Lệnh cử chỉ từ AI)
        elif feed_id == "gesture-log":
            gesture_cmd = str(payload)
            db.log_gesture(camera_id="CAM_01", gesture_name=gesture_cmd)

            # --- LOGIC ĐIỀU KHIỂN QUA CỬ CHỈ (BETA chưa áp dụng logic như báo cáo, chỉ minh họa) ---
            if gesture_cmd == "Clapping":
                device_id = "FAN" # Hoặc ID quạt nhà bạn đang set
                
                # 1. Lấy trạng thái của cái quạt đó trong nhà
                row = db.get_shared_device_state(device_id)
                if row:
                    state = json.loads(row["state_json"]) if row["state_json"] else {}
                    
                    # 2. Đảo ngược trạng thái
                    new_is_on = not state.get("isOn", False)
                    state["isOn"] = new_is_on
                    
                    # 3. CẬP NHẬT CHO TẤT CẢ APP CỦA MỌI NGƯỜI TRONG NHÀ
                    db.update_shared_device_state(device_id, json.dumps(state))
                    
                    # 4. Đóng gói và bắn xuống mạch YoloBit
                    is_on_val = 1 if new_is_on else 0
                    speed = int(state.get("speed", 50))
                    is_osc = 1 if state.get("isOscillating") else 0
                    is_track = 1 if state.get("isTracking") else 0
                    
                    packed_data = f"{is_on_val}:{speed:03d}:{is_osc}:{is_track}"
                    
                    mqtt.publish(f"device-{device_id.lower()}", packed_data)
                    db.log_device(device_id, is_on_val, "AI_Gesture_Auto")
                    print(f"-> AI tự động {'BẬT' if new_is_on else 'TẮT'} quạt cho toàn gia đình!")
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