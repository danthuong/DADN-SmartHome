import time
# IMPORT CÁI CLASS MÌNH VỪA VIẾT Ở TRÊN VÀO
from mqtt_client import SmartHomeMQTT 
from modules.human_detection.human_detector import HumanDetector

# 1. Khởi động AI
print("[Khởi động] Đang tải Model YOLO...")
ai_module = HumanDetector(model_path='yolov8n.pt', conf_threshold=0.7)

# 2. Khởi động mạng MQTT (Chỉ tốn đúng 2 dòng)
mqtt = SmartHomeMQTT()
mqtt.start()

last_state = -1

# 3. Vòng lặp chính
print("[SYSTEM] Camera Phát hiện người đã sẵn sàng!")
while True:
    trang_thai_hien_dien = ai_module.scan_and_display()
    
    if trang_thai_hien_dien == -1: 
        break
    
    if trang_thai_hien_dien != last_state:
        print(f"[{time.strftime('%H:%M:%S')}] Có người? -> {trang_thai_hien_dien}")
        mqtt.publish("human-detect-ai", trang_thai_hien_dien)
        last_state = trang_thai_hien_dien
    
    if ai_module.check_exit():
        break

ai_module.cleanup()