import cv2
import sys
import os
import time
import numpy as np
from Adafruit_IO import MQTTClient
from dotenv import load_dotenv

from modules.human_detection.human_detector import HumanDetector
from modules.motion_detection.kp_extractor import HandExtractor
from database.db_manager import DatabaseManager 

load_dotenv()
# ==========================================
# CẤU HÌNH VẼ KHUNG XƯƠNG TAY (MEDIAPIPE
# ==========================================
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),         
    (0, 5), (5, 6), (6, 7), (7, 8),         
    (5, 9), (9, 10), (10, 11), (11, 12),    
    (9, 13), (13, 14), (14, 15), (15, 16),  
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) 
]

def draw_hand_skeleton_from_array(frame, kp_array, w, h):
    points = kp_array.reshape(21, 3)
    pixel_points = []
    for p in points:
        cx, cy = int(p[0] * w), int(p[1] * h)
        pixel_points.append((cx, cy))
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1) 

    for connection in HAND_CONNECTIONS:
        start_idx, end_idx = connection[0], connection[1]
        if start_idx < len(pixel_points) and end_idx < len(pixel_points):
            pt1 = pixel_points[start_idx]
            pt2 = pixel_points[end_idx]
            cv2.line(frame, pt1, pt2, (255, 0, 0), 2)

# ==========================================
# CẤU HÌNH ADAFRUIT IO & MQTT CALLBACKS
# ==========================================
AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")
# Các tham số cấu hình và Ngưỡng mặc định
current_temp = 0
current_light = 0
threshold_temp = 30.0
threshold_light = 100.0
db = DatabaseManager()

def connected(client):
    print("[MQTT] Kết nối thành công tới Adafruit IO ...")
    client.subscribe("human-detect-pir") 
    client.subscribe("env-temp") 
    client.subscribe("env-light")   
    client.subscribe("setting-temp")  
    client.subscribe("setting-light") 

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

# ==========================================
# HÀM MAIN: KẾT HỢP IOT VÀ AI
# ==========================================
def main():
    # 1. KHỞI TẠO AI MODULES
    print("[SYSTEM] Khởi tạo hệ thống AI...")
    yolo_ai = HumanDetector(model_path='models/yolov8x.pt', conf_threshold=0.6)
    mp_ai = HandExtractor(mp_model='models/gesture_recognizer.task')

    # 2. KHỞI TẠO MQTT CLIENT
    print("[SYSTEM] Khởi tạo kết nối MQTT...")
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

    # 3. BIẾN QUẢN LÝ TRẠNG THÁI IOT
    last_state = -1
    mqtt_last_time = time.time()
    last_seen_time = time.time() 
    DELAY_TURN_OFF = 3.0          
    UPDATE_TIME = 10.0            

    # 4. BIẾN QUẢN LÝ FPS & MEDIAPIPE
    frame_count = 0
    cached_final_data = {}
    fps_start_time = time.time()
    display_fps = 0

    print("[SYSTEM] Hệ thống đã sẵn sàng hoạt động. Bấm 'q' để thoát.")

    while True:
        # --- Bước 1: HUMAN DETECTOR trả về 3 thứ: trạng thái có người hay không, frame đã vẽ bounding box, và dictionary chứa bounding box của từng người (key là track_id) ---
        trang_thai_hien_dien, frame, persons_bbox = yolo_ai.scan_and_display()
        if trang_thai_hien_dien == -1: 
            print("[HUMAN_DETECTION_ERROR] Mất kết nối Camera!")
            break

        current_time = time.time()
        h, w, _ = frame.shape
        frame_count += 1

        # --- BƯỚC 2: LOGIC LỌC NHIỄU (DEBOUNCE) CHO IOT ---
        if trang_thai_hien_dien == 1:
            last_seen_time = current_time
            trang_thai_chinh_thuc = 1
        else:
            if (current_time - last_seen_time) > DELAY_TURN_OFF:
                trang_thai_chinh_thuc = 0 
            else:
                trang_thai_chinh_thuc = 1 

        # --- BƯỚC 3: XỬ LÝ PUBLISH MQTT & DATABASE ---
        if (trang_thai_chinh_thuc != last_state) or (current_time - mqtt_last_time > UPDATE_TIME):
            print(f"[{time.strftime('%H:%M:%S')}] Trang thái chính thức: {trang_thai_chinh_thuc}")
            client.publish("human-detect-ai", trang_thai_chinh_thuc)
            db.log_sensor("AI_CAM", trang_thai_chinh_thuc, user_name="Thinh")

            # Logic điều khiển thiết bị
            if trang_thai_chinh_thuc == 1:
                status_fan = 1 if current_temp > threshold_temp else 0
                reason_fan = f"HOT: {current_temp}C > {threshold_temp}C" if status_fan else f"COOL: {current_temp}C <= {threshold_temp}C"
                db.log_device("FAN", status_fan, reason_fan, threshold_temp)
                
                status_led = 1 if current_light < threshold_light else 0
                reason_led = f"DARK: {current_light}lux < {threshold_light}lux" if status_led else f"BRIGHT: {current_light}lux >= {threshold_light}lux"
                db.log_device("LED", status_led, reason_led, threshold_light)
            else:
                db.log_device("FAN", 0, "Phát hiện không có người", threshold_temp)
                db.log_device("LED", 0, "Phát hiện không có người", threshold_light)

            last_state = trang_thai_chinh_thuc
            mqtt_last_time = current_time

        # --- BƯỚC 4: XỬ LÝ MEDIAPIPE LẤY KEYPOINT ---
        if trang_thai_hien_dien == 1:
            timestamp_ms = int(current_time * 1000)
            final_data = mp_ai.extract_hands(frame, persons_bbox, timestamp_ms)

            # Vẽ xương tay và ID
            for track_id, data in final_data.items():
                x1, y1, x2, y2 = data["bbox"]
                hands_count = len(data["hands"])
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {track_id} - Tay: {hands_count}", 
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                for hand_array in data["hands"]:
                    draw_hand_skeleton_from_array(frame, hand_array, w, h)
        else:
            final_data = {}

        # --- BƯỚC 5: TÍNH TOÁN FPS VÀ SHOW ẢNH ---
        elapsed_time = time.time() - fps_start_time
        if elapsed_time > 0:
            display_fps = 1 / elapsed_time
        fps_start_time = time.time()
        
        cv2.putText(frame, f"FPS: {int(display_fps)}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        cv2.imshow("Smart Home AI", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Dọn dẹp tài nguyên
    yolo_ai.cleanup()
    mp_ai.cleanup()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()