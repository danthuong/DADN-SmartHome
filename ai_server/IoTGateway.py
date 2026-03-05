import sys
import time
import cv2
import serial.tools.list_ports
import serial
from Adafruit_IO import MQTTClient

from modules.human_detection.human_detector import HumanDetector
from database.db_manager import DatabaseManager 
# ==========================================
# CẤU HÌNH 3 KHÓA THÔNG SỐ ADAFRUIT IO
# ==========================================
AIO_USERNAME = "thinhphan2313306"
AIO_KEY = "aio_VWuR71QDMpqjdnUvo65mq4sZKtmI"
AIO_HUMAN_DETECT_FEED = "bbc-temp"  # Tạm dùng bbc-temp, sau này đổi tên trên Adafruit thì sửa ở đây
# ==========================================
# Hàm đọc cổng của cái USB kết nối microbit,
# ==========================================
def getPort():
    ports = serial.tools.list_ports.comports()
    N = len(ports)
    commPort = "None"
    for i in range(0, N):
        port = ports[i]
        strPort = str(port)
        if "USB Serial Device" in strPort:
            splitPort = strPort.split(" ")
            commPort = (splitPort[0])
    return commPort
# ==========================================
# Định nghĩa các hàm cho giao thức MQTT
# ==========================================
def connected(client):
    print("[MQTT] Kết nối thành công tới Adafruit IO ...")
    client.subscribe(AIO_HUMAN_DETECT_FEED)

def subscribe(client, userdata, mid, granted_qos):
    print("[MQTT] Đã Subscribe thành công ... ")

def disconnected(client):
    print("[MQTT] Đã ngắt kết nối ... ")
    sys.exit(1)

def message(client, feed_id, payload):
    print(f"[MQTT] Nhận dữ liệu từ {feed_id}: {payload}")
    
    # Đẩy lệnh xuống mạch Microbit
    global ser
    if ser is not None:
        chuoi_gui = str(payload) + "#"
        ser.write(chuoi_gui.encode('utf-8'))
        print(f"[SERIAL] Đã đẩy xuống mạch: {chuoi_gui}")

print("[SYSTEM] Đang khởi động IoTGateway...")
# tạo file database để lưu các thông số, dữ liệu cần thiết (trong tương lai sẽ bổ sung thêm lưu cái gì, hiện tại chưa cụ thể)
db = DatabaseManager()
###################################################################################
############# PHẦN NÀY mọi người để phần khởi tạo từng module vào đây #############
# Khởi tạo Module Human Detection
ai_module = HumanDetector(model_path='models/yolov8n.pt', conf_threshold=0.7)
##################################################################################
# Khởi tạo kết nối Serial đến mạch
portName = getPort()
ser = None
if portName != "None":
    print(f"[SYSTEM] Đã tìm thấy mạch tại cổng: {portName}")
    try:
        ser = serial.Serial(port=portName, baudrate=115200)
    except Exception as e:
        print(f"[SYSTEM_ERROR] Không thể mở cổng Serial: {e}")
else:
    print("[SYSTEM_ERROR] Không tìm thấy cổng!")

# Khởi tạo kết nối mạng MQTT
client = MQTTClient(AIO_USERNAME, AIO_KEY)
client.on_connect = connected
client.on_disconnect = disconnected
client.on_message = message
client.on_subscribe = subscribe

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
print("[SYSTEM] IoT Gateway đã sẵn sàng hoạt động.")

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
        print(f"[{time.strftime('%H:%M:%S')}] HUMAN_DETECTION_AI: {'CÓ NGƯỜI (1)' if trang_thai_chinh_thuc == 1 else 'KHÔNG (0)'}")
        try:
            client.publish(AIO_HUMAN_DETECT_FEED, trang_thai_chinh_thuc)
            db.log_environment(presence=trang_thai_chinh_thuc)
        except Exception as e:
            print(f"[SYSTEM] Không gửi được dữ liệu: {e}")

        last_state = trang_thai_chinh_thuc
        last_time = current_time
    # gõ q để thoát camera
    if ai_module.check_exit():
        break

# Dọn dẹp trước khi đóng
ai_module.cleanup()