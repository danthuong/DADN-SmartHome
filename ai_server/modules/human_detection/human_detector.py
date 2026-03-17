import cv2
import sys
import torch
import threading
import time
from ultralytics import YOLO

device = 'cuda' if torch.cuda.is_available() else 'cpu'

class HumanDetector:
    def __init__(self, model_path='models/yolov8x.pt', conf_threshold=0.6):
        print(f"[MODULE_HUMAN_DETECTION] Đang tải mô hình trên {device.upper()}...")
        self.model = YOLO(model_path)
        self.model.to(device) 
        self.conf_threshold = conf_threshold
        
        # Các biến dùng chung giữa các threads
        self.current_frame = None
        self.latest_state = 0
        self.latest_bbox = {}
        
        self.running = True
        self.lock = threading.Lock() # Khóa để tránh xung đột dữ liệu
        
        # Khởi động luồng chạy YOLO
        self.thread = threading.Thread(target=self._run_yolo_loop, daemon=True)
        self.thread.start()

    def update_frame(self, frame):
        """Hàm để luồng chính đẩy frame mới nhất vào cho YOLO"""
        with self.lock:
            self.current_frame = frame.copy()

    def get_latest_results(self):
        """Hàm để luồng chính lấy kết quả nhận diện mới nhất từ YOLO"""
        with self.lock:
            return self.latest_state, self.latest_bbox

    def _run_yolo_loop(self):
        """Hàm này chạy liên tục ở một luồng riêng (background thread)"""
        while self.running:
            with self.lock:
                frame_to_process = self.current_frame

            if frame_to_process is None:
                time.sleep(0.01) # Chờ một chút nếu chưa có frame
                continue

            # --- Chạy inference bằng YOLO ---
            h, w = frame_to_process.shape[:2]
            state = 0
            persons_bb = {}
            padding = 10

            results = self.model.track(frame_to_process, classes=[0], persist=True, verbose=False)
            
            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id.cpu().numpy()
                confs = results[0].boxes.conf.cpu().numpy()
                
                for box, track_id, conf in zip(boxes, track_ids, confs):
                    if conf >= self.conf_threshold:
                        state = 1 
                        x1, y1, x2, y2 = box.astype(int)
                        # Mở rộng bounding box
                        x1_new = max(0, x1 - padding)
                        y1_new = max(0, y1 - padding)
                        x2_new = min(w, x2 + padding)
                        y2_new = min(h, y2 + padding)
                        persons_bb[int(track_id)] = [x1_new, y1_new, x2_new, y2_new]

            # Cập nhật kết quả vào biến dùng chung
            with self.lock:
                self.latest_state = state
                self.latest_bbox = persons_bb

            time.sleep(0.01)

    def cleanup(self):
        self.running = False
        self.thread.join() 
        print("[MODULE_HUMAN_DETECTION] Đã đóng YOLO.")