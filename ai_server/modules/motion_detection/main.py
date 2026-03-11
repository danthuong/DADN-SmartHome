import cv2
import sys
import os
import time
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))

if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)
    
YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8x.pt")
MP_MODEL_PATH = os.path.join(ROOT_DIR, "models", "gesture_recognizer.task")

from modules.human_detection.human_detector import HumanDetector
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
    yolo_ai = HumanDetector(model_path=YOLO_MODEL_PATH, conf_threshold=0.6)
    mp_ai = HandExtractor(mp_model=MP_MODEL_PATH, max_hands=4)

    cap = cv2.VideoCapture(1) # Thay đổi ID camera nếu cần
    if not cap.isOpened():
        print("[ERROR] Không thể mở Camera!")
        sys.exit(1)

    print("[SYSTEM] Bắt đầu chạy Real-time. Bấm 'q' để thoát.")

    # --- KHỞI TẠO BỘ ĐẾM LOG ---
    start_time = time.time()
    mp_frame_count = 0
    total_hands_detected = 0
    last_mp_timestamp = 0 # Dùng để tránh cộng dồn trùng lặp

    print("[SYSTEM] Bắt đầu chạy Real-time. Bấm 'q' để thoát.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1)

        # Đẩy frame vào các luồng xử lý ngầm
        current_time = time.time()
        timestamp_ms = int(current_time * 1000)
        
        yolo_ai.update_frame(frame)
        mp_ai.process_frame_async(frame, timestamp_ms)

        # Lấy kết quả mới nhất
        state, persons_bbox = yolo_ai.get_latest_results()
        
        # Hàm get_latest_results của MediaPipe giờ chỉ cần trả về 4 biến (tay, cử chỉ, ảnh, fps)
        hands_data, gestures_data, mp_frame, mp_fps = mp_ai.get_latest_results()

        # Chọn frame để hiển thị (Ưu tiên mp_frame để khớp xương 100%)
        if mp_frame is not None:
            display_frame = mp_frame.copy()
        else:
            display_frame = frame.copy()

        h, w = display_frame.shape[:2]

        # --- VẼ LÊN MÀN HÌNH ---
        # 1. Vẽ Box YOLO
        if persons_bbox:
            for track_id, bbox in persons_bbox.items():
                x1, y1, x2, y2 = bbox
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(display_frame, f"Person ID: {track_id}", (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 2. Vẽ xương tay và Cử chỉ
        for idx, hand_array in enumerate(hands_data):
            draw_hand_skeleton_from_array(display_frame, hand_array, w, h)
            gesture = gestures_data[idx] if idx < len(gestures_data) else "None"
            cv2.putText(display_frame, f"Gest: {gesture}", (20, 100 + (idx*40)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)

        # Hiển thị FPS trên góc màn hình
        cv2.putText(display_frame, f"MP FPS: {mp_fps}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 3)

        cv2.imshow("Smart Home AI", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Dọn dẹp
    cap.release()
    yolo_ai.cleanup()
    mp_ai.cleanup()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()