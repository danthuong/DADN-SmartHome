import cv2
import sys
from ultralytics import YOLO

class HumanDetector:
    def __init__(self, model_path='models/yolov8n.pt', conf_threshold=0.7):
        """
        Khởi tạo module Phát hiện người.
        - model_path: Đường dẫn tới file trọng số YOLOv8 Nano.
        - conf_threshold: Ngưỡng tin cậy (mặc định 70%).
        """
        print("[MODULE_HUMAN_DETECTION] Đang tải mô hình Human Detection (YOLOv8n)...")
        # Load model 1 lần duy nhất khi khởi động hệ thống để tránh lag
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        # Bật Camera ngay khi khởi tạo Module
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("[MODULE_HUMAN_DETECTION_ERROR] Module không thể mở Camera!")
            sys.exit(1)
    def scan_and_display(self):
        """Hàm này tự chụp ảnh, nhận diện, và vẽ bounding box lên màn hình, đồng thời trả về trạng thái cho gateway 
        (trạng thái là có người hoặc không có người)"""
        ret, frame = self.cap.read()
        if not ret:
            return -1 # lỗi ko có hình
        trang_thai_hien_dien = 0
        # Logic nhận diện bởi con YOLO
        # 1 số cái tham số, classes = [0] để chỉ tìm người (đỡ lag)
        # verbose = false để ko ghi mấy cái log dư thừa do YOLO in ra
        results = self.model(frame, classes = [0], verbose = False)
        for box in results[0].boxes:
            class_id = int(box.cls[0])
            conf = float(box.conf[0])
            if class_id == 0 and conf >= self.conf_threshold:
                trang_thai_hien_dien = 1 # có người
                break
        # vẽ boundingbox
        khung_hinh_da_ve = results[0].plot()

        cv2.imshow("Smart Home - Human Detection by Camera + AI", khung_hinh_da_ve)
        return trang_thai_hien_dien

    def check_exit(self):
        """Hàm kiểm tra xem người dùng có bấm phím 'q' để thoát không"""
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return True
        return False

    def cleanup(self):
        """Dọn dẹp tài nguyên phần cứng"""
        self.cap.release()
        cv2.destroyAllWindows()
        print("[MODULE_HUMAN_DETECTION] Đã đóng AI Camera.")