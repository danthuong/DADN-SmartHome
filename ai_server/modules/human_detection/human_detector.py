import cv2
from ultralytics import YOLO

class HumanDetector:
    def __init__(self, model_path='ai_server/models/yolov8n.pt', conf_threshold=0.7):
        """
        Khởi tạo module Phát hiện người.
        - model_path: Đường dẫn tới file trọng số YOLOv8 Nano.
        - conf_threshold: Ngưỡng tin cậy (mặc định 70%).
        """
        print("[INFO] Đang tải mô hình Human Detection (YOLOv8n)...")
        # Load model 1 lần duy nhất khi khởi động hệ thống để tránh lag
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold

    def process_frame(self, frame):
        """
        Nhận vào 1 khung hình (frame), xử lý và trả về kết quả.
        - Return: (has_human, annotated_frame)
            + has_human (int): 1 nếu có người, 0 nếu không có.
            + annotated_frame (numpy array): Khung hình đã được vẽ Bounding Box.
        """
        # Quét khung hình tìm Person (class 0)
        results = self.model(frame, classes=[0], conf=self.conf_threshold)
        
        # Lấy khung hình đã được AI vẽ sẵn Bounding Box
        annotated_frame = results[0].plot()
        
        # Kiểm tra xem có bao nhiêu Bounding Box được vẽ (có bao nhiêu người)
        if len(results[0].boxes) > 0:
            has_human = 1
        else:
            has_human = 0
            
        return has_human, annotated_frame
    
if __name__ == "__main__":
    # Đoạn code này chỉ chạy khi bạn chạy trực tiếp file này để test module.
    # Khi main.py import module này, đoạn code dưới đây sẽ tự động bị bỏ qua.
    
    detector = HumanDetector(model_path='yolov8n.pt') # Chạy test thì trỏ file ở thư mục hiện tại
    cap = cv2.VideoCapture(0)

    print("[INFO] Bắt đầu test độc lập module Human Detection. Nhấn 'q' để thoát.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Ném frame vào class để xử lý
        trang_thai, hinh_da_ve = detector.process_frame(frame)
        
        # In trạng thái ra terminal
        print(f"Trạng thái hiện diện: {'CÓ NGƯỜI' if trang_thai == 1 else 'KHÔNG'}")
        
        # Hiển thị lên màn hình
        cv2.imshow("Test Module Human Detection", hinh_da_ve)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
            
    cap.release()
    cv2.destroyAllWindows()