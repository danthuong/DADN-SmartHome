import time
import sys

from mqtt_client import SmartHomeMQTT
from database.db_manager import DatabaseManager 

db = DatabaseManager()

# ==========================================
# ĐỊNH NGHĨA CÁC HÀM LẮNG NGHE CHO THƯ KÝ
# ==========================================

def thuky_on_connect(client):
    print("\n[LOGGER] Đã kết nối Đám mây. Thư ký bắt đầu vểnh tai nghe...")
    
    # Đăng ký nghe ngóng CẢM BIẾN & AI
    client.subscribe("human-detect-pir") 
    client.subscribe("env-temp") 
    client.subscribe("env-light") 
    client.subscribe("human-detect-ai") # Nghe máy chạy YOLO (run_human.py)
    # ngưỡng nhiệt độ bật tắt quạt và ngưỡng sáng bật tắt đèn
    client.subscribe("setting-temp")
    client.subscribe("setting-light")
    # Đăng ký nghe ngóng THIẾT BỊ (YoloBit tự bật/tắt dưới nhà)
    client.subscribe("device-fan")
    client.subscribe("device-led")
    
    # Nếu sau này có FaceID hay Cử chỉ thì cứ thêm vào đây:
    # client.subscribe("face-id-log")
    # client.subscribe("gesture-log")

def thuky_on_message(client, feed_id, payload):
    try:
        val = float(payload) # Chuyển dữ liệu nhận được thành số
        
        # NHÓM LƯU LOG CẢM BIẾN
        if feed_id == "human-detect-pir":
            db.log_sensor("PIR", val)
            print(f"[{time.strftime('%H:%M:%S')}] Đã ghi Log: PIR = {val}")
            
        elif feed_id == "env-temp":
            db.log_sensor("TEMP", val)
            
        elif feed_id == "env-light":
            db.log_sensor("LIGHT", val)
            
        # --- NHÓM LƯU LOG TRẠNG THÁI AI ---
        elif feed_id == "human-detect-ai":
            db.log_camera(camera_id="CAM_NODE_01", has_human=val)
            print(f"[{time.strftime('%H:%M:%S')}] Đã ghi Log: Camera YOLO = {val}")
            
        # --- NHÓM LƯU LOG THIẾT BỊ ---
        elif feed_id == "device-fan":
            db.log_device("FAN", val, trigger_source="Hardware_Auto")
            print(f"[{time.strftime('%H:%M:%S')}] Đã ghi Log: Quạt = {val}")
            
        elif feed_id == "device-led":
            db.log_device("LED", val, trigger_source="Hardware_Auto")
            print(f"[{time.strftime('%H:%M:%S')}] Đã ghi Log: Đèn = {val}")
        # --- nhóm ngưỡng có thể setting từ người dùng (Dùng chung bảng Thiết bị) ---
        elif feed_id == "setting-temp":
            # Coi SET_TEMP là device_id, val là trạng thái, Mobile_App là nguyên nhân
            db.log_device(device_id="SET_TEMP", status=val, trigger_source="Mobile_App_Update")
            print(f"[{time.strftime('%H:%M:%S')}] App vừa đổi Ngưỡng Nhiệt độ: {val}")
            
        elif feed_id == "setting-light":
            db.log_device(device_id="SET_LIGHT", status=val, trigger_source="Mobile_App_Update")
            print(f"[{time.strftime('%H:%M:%S')}] App vừa đổi Ngưỡng Ánh sáng: {val}")
    except Exception as e:
        # Nếu payload không phải là số (ví dụ chuỗi "Thinh vuot qua cong") thì xử lý riêng
        print(f"[CẢNH BÁO] Lỗi ghi chép hoặc dữ liệu không phải số: {payload} từ kênh {feed_id}")

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