import sys
import time
from Adafruit_IO import MQTTClient

from modules.human_detection.human_detector import HumanDetector
from database.db_manager import DatabaseManager 
# ==========================================
# CẤU HÌNH 3 KHÓA THÔNG SỐ ADAFRUIT IO
# ==========================================
AIO_USERNAME = "thinhphan2313306"
AIO_KEY = "aio_VWuR71QDMpqjdnUvo65mq4sZKtmI"
AIO_HUMAN_DETECT_FEED = "human-detect-ai"  # Tạm dùng bbc-temp, sau này đổi tên trên Adafruit thì sửa ở đây
#Các tham số cấu hình và Ngưỡng mặc định (nếu chưa nhận được từ Dashboard)
current_temp = 0
current_light = 0
threshold_temp = 30.0
threshold_light = 100.0
# ==========================================
# Định nghĩa các hàm cho giao thức MQTT
# ==========================================
def connected(client):
    print("[MQTT] Kết nối thành công tới Adafruit IO ...")
    client.subscribe("human-detect-pir") # kênh nhận tín hiệu phát hiện bằng hồng ngoại
    client.subscribe("env-temp") #kênh nhận nhiệt độ cảm biến đo được
    client.subscribe("env-light")   # kênh nhận độ sáng môi trường đo được
    client.subscribe("setting-temp")  # Kênh nhận ngưỡng nhiệt độ từ Dashboard
    client.subscribe("setting-light") # Kênh nhận ngưỡng ánh sáng từ Dashboard
def disconnected(client):
    print("[MQTT] Đã ngắt kết nối ... ")
    sys.exit(1)
def message(client, feed_id, payload):
    global current_temp, current_light, threshold_temp, threshold_light
    try:
        val = float(payload)
        if feed_id == "human-detect-pir":
            db.log_sensor("PIR", val)
            print(f"[MQTT] PIR status: {val}")
        elif feed_id == "env-temp":
            current_temp = val
            db.log_sensor("TEMP", val)
        elif feed_id == "env-light":
            current_light = val
            db.log_sensor("LIGHT", val)
        elif feed_id == "setting-temp":
            threshold_temp = val
            print(f"[SETTING] Ngưỡng nhiệt độ mới: {val}")
        elif feed_id == "setting-light":
            threshold_light = val
            print(f"[SETTING] Ngưỡng ánh sáng mới: {val}")
    except Exception as e:
        print(f"Lỗi nhận tin: {e}")
# tạo file database để lưu các thông số, dữ liệu cần thiết (trong tương lai sẽ bổ sung thêm lưu cái gì, hiện tại chưa cụ thể)
db = DatabaseManager()
###################################################################################
############# PHẦN NÀY mọi người để phần khởi tạo từng module vào đây #############
# Khởi tạo Module Human Detection
ai_module = HumanDetector(model_path='models/yolov8n.pt', conf_threshold=0.7)
##################################################################################

# Khởi tạo kết nối mạng MQTT
client = MQTTClient(AIO_USERNAME, AIO_KEY)
client.on_connect = connected
client.on_disconnect = disconnected
client.on_message = message
try:
    client.connect()
    client.loop_background()
except Exception as e:
    print(f"[MQTT_ERROR] Không thể kết nối đến server Adafruit: {e}")
    sys.exit(1)
# Biến lưu trữ chống spam trạng thái
last_state = -1
last_time = time.time()
#lọc nhiễu nhấp nháy tín hiệu
last_seen_time = time.time()  # Ghi nhớ thời điểm cuối cùng nhìn thấy người
DELAY_TURN_OFF = 3.0          # Số giây chờ trước khi chính thức chốt là "Không có người"
UPDATE_TIME = 10.0            # số giây cập nhật lại nếu ko có sự thay đổi trạng thái
print("[SYSTEM] Các Module đã sẵn sàng hoạt động.")

while True:
    # MODULE HUMAN DETECTION
    trang_thai_hien_dien = ai_module.scan_and_display()
    
    if trang_thai_hien_dien == -1: 
        print("[HUMAN_DETECTION_ERROR] Mất kết nối Camera!")
        break

    current_time = time.time()
    if trang_thai_hien_dien == 1:
        # Nếu đang thấy người -> Liên tục cập nhật lại thời điểm nhìn thấy
        last_seen_time = current_time
        trang_thai_chinh_thuc = 1
    else:
        if (current_time - last_seen_time) > DELAY_TURN_OFF:
            trang_thai_chinh_thuc = 0 # đã quá thời hạn và không thấy ai -> Xác nhận ko có người
        else:
            trang_thai_chinh_thuc = 1 # nếu còn trong thời hạn thì ta tạm coi là sai số của YOLO
    if (trang_thai_chinh_thuc != last_state) or (current_time - last_time > UPDATE_TIME):
        print(f"[{time.strftime('%H:%M:%S')}] Trang thái: {trang_thai_chinh_thuc}")
        
        # Gửi AI status lên Cloud cho Micro:bit
        client.publish("human-detect-ai", trang_thai_chinh_thuc)
        
        # Lưu Log cảm biến AI
        db.log_camera(camera_id="CAM_01", has_human=trang_thai_chinh_thuc)

        # LOGIC TINH CHỈNH THIẾT BỊ
        if trang_thai_chinh_thuc == 1:
            # Kiểm tra nhiệt độ
            status_fan = 1 if current_temp > threshold_temp else 0
            # Tạo trigger_source rõ ràng, ví dụ: "YOLO_Auto_32.5C"
            trigger_fan = f"YOLO_Auto_{current_temp}C"
            db.log_device("FAN", status_fan, trigger_source=trigger_fan)
            client.publish("device-fan", status_fan)
            # Kiểm tra ánh sáng
            status_led = 1 if current_light < threshold_light else 0
            trigger_led = f"YOLO_Auto_{current_light}lux"
            db.log_device("LED", status_led, trigger_source=trigger_led)
            client.publish("device-led", status_led)
        else:
            # Không có người thì mặc định lưu log Tắt
            db.log_device("FAN", 0, trigger_source="YOLO_NoHuman_Timeout")
            db.log_device("LED", 0, trigger_source="YOLO_NoHuman_Timeout")
            client.publish("device-fan", 0)
            client.publish("device-led", 0)
        last_state = trang_thai_chinh_thuc
        last_time = current_time
    
    # gõ q để thoát camera
    if ai_module.check_exit():
        break

# Dọn dẹp trước khi đóng
ai_module.cleanup()