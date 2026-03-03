import cv2
import time

# IMPORT CÁC MODULE VÀO ĐÂY
from mqtt_client import setup_mqtt
from modules.human_detection.human_detector import HumanDetector
from database.db_manager import DatabaseManager 
# ==========================================
# 1. CẤU HÌNH THÔNG SỐ ADAFRUIT IO
# ==========================================
AIO_USERNAME = "thinhphan2313306"
AIO_KEY = "aio_VWuR71QDMpqjdnUvo65mq4sZKtmI"
AIO_HUMAN_DETECT_FEED = "bbc-temp"  # Tạm dùng bbc-temp, sau này đổi tên trên Adafruit thì sửa ở đây

# ==========================================
# 2. KHỞI TẠO CÁC THÀNH PHẦN
# ==========================================
print("[MAIN] Đang khởi động hệ thống Smart Home...")

# Khởi tạo client MQTT (Đúng chuẩn format giáo trình)
client = setup_mqtt(AIO_USERNAME, AIO_KEY)

# Khởi tạo AI Module
human_ai = HumanDetector(model_path='models/yolov8n.pt', conf_threshold=0.7)

# Khởi tạo Camera
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("[LỖI] Không mở được Camera")
    exit()

# Biến lưu trữ chống spam mạng
last_state = -1
last_time = time.time()

print("[MAIN] Khởi tạo Database...")
db = DatabaseManager()

print("[MAIN] Hệ thống bắt đầu quét. Nhấn phím 'q' để tắt.")

# ==========================================
# 3. VÒNG LẶP CHÍNH (MAIN LOOP)
# ==========================================
while True:
    ret, frame = cap.read()
    if not ret: 
        break

    # --- ĐƯA HÌNH CHO AI XỬ LÝ ---
    trang_thai_nguoi, khung_hinh_da_ve = human_ai.process_frame(frame)
    
    current_time = time.time()
    
    # --- LOGIC ĐẨY LÊN CLOUD ---
    if (trang_thai_nguoi != last_state) or (current_time - last_time > 10):
        print(f"[{time.strftime('%H:%M:%S')}] Pushing: {'CÓ NGƯỜI (1)' if trang_thai_nguoi == 1 else 'KHÔNG (0)'}")
        
        # Dùng đối tượng 'client' để publish theo đúng chuẩn
        try:
            client.publish(AIO_HUMAN_DETECT_FEED, trang_thai_nguoi)
        except Exception as e:
            print(f"[LỖI] Không gửi được dữ liệu: {e}")
        db.log_environment(presence=trang_thai_nguoi)
        last_state = trang_thai_nguoi
        last_time = current_time

    # --- HIỂN THỊ LÊN MÀN HÌNH ---
    cv2.imshow("Smart Home - AI Edge Gateway", khung_hinh_da_ve)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Dọn dẹp trước khi đóng
cap.release()
cv2.destroyAllWindows()