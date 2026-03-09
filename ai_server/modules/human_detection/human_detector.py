import cv2
import sys
import torch
from ultralytics import YOLO

# xài cuda cho lẹ
print(torch.version.cuda)
print(torch.cuda.is_available())
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(f"[SYSTEM] Đang sử dụng thiết bị: {device.upper()}")

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
        self.model.to(device) 

        self.conf_threshold = conf_threshold
        self.cap = cv2.VideoCapture(1)
        if not self.cap.isOpened():
            print("[MODULE_HUMAN_DETECTION_ERROR] Module không thể mở Camera!")
            sys.exit(1)

    def scan_and_display(self, padding = 50):
        """Hàm này tự chụp ảnh, nhận diện, và vẽ bounding box lên màn hình, đồng thời trả về trạng thái cho gateway 
        (trạng thái là có người hoặc không có người)"""
        ret, frame = self.cap.read()
        if not ret:
            return -1 
        
        h, w = frame.shape[:2]
        state = 0
        persons_bb = {}
        results = self.model.track(frame, classes = [0], persist = True, verbose = False)
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()
            
            for box, track_id, conf in zip(boxes, track_ids, confs):
                if conf >= self.conf_threshold:
                    state = 1 

                    x1, y1, x2, y2 = box.astype(int)
                    # Mở rộng bounding box thêm một khoảng padding để dễ dàng nhận diện tay hơn
                    x1_new = max(0, x1 - padding)
                    y1_new = max(0, y1 - padding)
                    x2_new = min(w, x2 + padding)
                    y2_new = min(h, y2 + padding)
                    persons_bb[int(track_id)] = [x1_new, y1_new, x2_new, y2_new]

        return state, frame, persons_bb

    # def check_exit(self):
    #     """Hàm kiểm tra xem người dùng có bấm phím 'q' để thoát không"""
    #     if cv2.waitKey(1) & 0xFF == ord('q'):
    #         return True
    #     return False

    def cleanup(self):
        """Dọn dẹp tài nguyên phần cứng"""
        self.cap.release()
        print("[MODULE_HUMAN_DETECTION] Đã đóng AI Camera.")