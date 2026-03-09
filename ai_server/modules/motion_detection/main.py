import cv2
import sys
import os
import time
import numpy as np

sys.path.append(os.path.abspath("../"))

from human_detection.human_detector import HumanDetector
from kp_extractor import HandExtractor

# Khai báo các điểm nối ngón tay để vẽ xương
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),         # Ngón cái
    (0, 5), (5, 6), (6, 7), (7, 8),         # Ngón trỏ
    (5, 9), (9, 10), (10, 11), (11, 12),    # Ngón giữa
    (9, 13), (13, 14), (14, 15), (15, 16),  # Ngón áp út
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20) # Ngón út
]

def draw_hand_skeleton_from_array(frame, kp_array, w, h):
    """
    Hỗ trợ vẽ khung xương tay từ mảng 1 chiều (63 phần tử)
    """
    # Chuyển mảng 1 chiều về lại ma trận 21x3 (x, y, z)
    points = kp_array.reshape(21, 3)
    
    pixel_points = []
    for p in points:
        cx, cy = int(p[0] * w), int(p[1] * h)
        pixel_points.append((cx, cy))
        # Vẽ các khớp (Points) màu Đỏ
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1) 

    # Vẽ các đường nối (Xương) màu Xanh dương
    for connection in HAND_CONNECTIONS:
        start_idx, end_idx = connection[0], connection[1]
        if start_idx < len(pixel_points) and end_idx < len(pixel_points):
            pt1 = pixel_points[start_idx]
            pt2 = pixel_points[end_idx]
            cv2.line(frame, pt1, pt2, (255, 0, 0), 2)


def main():
    # Khởi tạo 2 module độc lập
    yolo_ai = HumanDetector(model_path='yolov8x.pt', conf_threshold=0.6)
    mp_ai = HandExtractor(mp_model='gesture_recognizer.task')

    print("[SYSTEM] Bắt đầu chạy Real-time. Bấm 'q' để thoát.")

    # --- KHỞI TẠO BỘ ĐẾM LOG ---
    start_time = time.time()
    mp_frame_count = 0
    total_hands_detected = 0

    while True:
        # 1. Quét bằng YOLO
        state, frame, persons_bbox = yolo_ai.scan_and_display()

        if state == -1:
            break

        # Lấy kích thước ảnh để tính toán tọa độ vẽ tay
        h, w, _ = frame.shape

        # 2. Nếu YOLO thấy người -> Gọi MediaPipe
        if state == 1:
            timestamp_ms = int(time.time() * 1000)
            
            # Kết hợp data 2 bên
            final_data = mp_ai.extract_hands(frame, persons_bbox, timestamp_ms)

            # Cập nhật số frame MediaPipe đã chạy
            mp_frame_count += 1

            # --- VẼ THÔNG TIN LÊN MÀN HÌNH CHÍNH ---
            for track_id, data in final_data.items():
                x1, y1, x2, y2 = data["bbox"]
                hands_count = len(data["hands"])
                
                # Cộng dồn số bàn tay trích xuất được
                total_hands_detected += hands_count
                
                # Vẽ Box và ID người
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"ID: {track_id} - Tay: {hands_count}", 
                            (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Vẽ từng bàn tay của người này
                for hand_array in data["hands"]:
                    draw_hand_skeleton_from_array(frame, hand_array, w, h)

        # --- LOG THỐNG KÊ SAU MỖI 1 GIÂY ---
        current_time = time.time()
        elapsed_time = current_time - start_time
        
        if elapsed_time >= 1.0:
            if state == 1:
                print(f"[LOG] Pipeline FPS: {mp_frame_count} | Số tay trích xuất/giây: {total_hands_detected}")
            else:
                print("[LOG] Không có người, Pipeline đang chạy ở max tốc độ (YOLO only)...")
                
            # Reset bộ đếm cho giây tiếp theo
            start_time = current_time
            mp_frame_count = 0
            total_hands_detected = 0

        # Trạng thái bằng 0 (không có người) thì nó chỉ vẽ hình cam bình thường
        cv2.imshow("Smart Home AI", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    yolo_ai.cleanup()
    mp_ai.cleanup()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()