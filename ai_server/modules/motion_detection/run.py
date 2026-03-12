import os
import sys

# 1. Tắt log của TensorFlow và MediaPipe thông qua biến môi trường
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'      # Tắt log TensorFlow (0: All, 3: Fatal only)
os.environ['GLOG_minloglevel'] = '3'         # Tắt log Google Log (MediaPipe)
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'       # Tắt log OpenCV

import math
import cv2
import time
import numpy as np
import pandas as pd
import pickle
import collections
from datetime import datetime
import threading
import pyaudio 
from audio_handler import AudioClapDetector

# Thiết lập đường dẫn hệ thống
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from modules.human_detection.human_detector import HumanDetector
from kp_extractor import HandExtractor

# --- CẤU HÌNH ĐƯỜNG DẪN ---
YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8n.pt")
GESTURE_MODEL_PATH = "gesture_model.pkl"
MP_MODEL_PATH = os.path.join(ROOT_DIR, "models", "gesture_recognizer.task")
AUDIO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yamnet.tflite")

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]

# --- BIẾN TOÀN CỤC ---
last_gesture_state = "none"
gesture_buffer = collections.deque(maxlen=5) 
clap_count = 0
last_clap_time = 0
is_clapping_now = False
is_clapping_current_time = False
prev_hand_count = 0
# Biến hỗ trợ xoay cổ tay (Mục tiêu mới)
last_tilt_angle = 0 

# --- CẤU HÌNH AUDIO ---
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
# Ngưỡng âm thanh (Bạn cần tự chỉnh số này tùy độ nhạy của Mic, ví dụ: 2000-8000)
AUDIO_THRESHOLD = 5000 

# --- BIẾN TOÀN CỤC DÙNG CHUNG GIỮA 2 LUỒNG ---
last_audio_clap_time = 0
audio_trigger_active = False

# 2. Hàm chặn luồng lỗi (stderr) ở cấp độ hệ thống (C++ level)
def silence_stderr():
    # Mở file "hố đen"
    devnull = os.open(os.devnull, os.O_WRONLY)
    # Ép luồng stderr (số 2) ghi vào hố đen thay vì màn hình
    os.dup2(devnull, 2)

# Gọi hàm này ngay lập tức trước khi import các thư viện nặng
silence_stderr()

def preprocess_landmarks(kp_array_63):
    points = kp_array_63.reshape(21, 3)[:, :2]
    temp_list = []
    base_x, base_y = points[0][0], points[0][1]
    for x, y in points:
        temp_list.append([x - base_x, y - base_y])
    max_val = max([max(abs(x), abs(y)) for x, y in temp_list])
    if max_val == 0: max_val = 1
    return np.array(temp_list).flatten() / max_val

def calculate_tilt_angle(kp_array_63):
    """Tính góc nghiêng của bàn tay dựa trên điểm 5 và 17"""
    points = kp_array_63.reshape(21, 3)
    p5 = points[5]  # Gốc ngón trỏ
    p17 = points[17] # Gốc ngón út
    
    # Tính góc dựa trên atan2 (kết quả trả về độ -180 đến 180)
    angle = math.degrees(math.atan2(p17[1] - p5[1], p17[0] - p5[0]))
    return angle

def send_mqtt_command(command):
    print(f"\033[92m[IOT COMMAND] >>> GỬI LỆNH: {command}\033[0m")

def draw_hand_skeleton(frame, kp_array, w, h):
    points = kp_array.reshape(21, 3)
    pixel_points = []
    for p in points:
        cx, cy = int(p[0] * w), int(p[1] * h)
        pixel_points.append((cx, cy))
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1) 
    for connection in HAND_CONNECTIONS:
        pt1 = pixel_points[connection[0]]
        pt2 = pixel_points[connection[1]]
        cv2.line(frame, pt1, pt2, (255, 0, 0), 2)
    return pixel_points[0] # Trả về vị trí cổ tay để ghi chữ

def main():
    global last_gesture_state, clap_count, last_clap_time, last_tilt_angle
        
    yolo_ai = HumanDetector(model_path=YOLO_MODEL_PATH, conf_threshold=0.6)
    mp_ai = HandExtractor(mp_model=MP_MODEL_PATH)
    
    audio_ai = AudioClapDetector(model_path=os.path.join(ROOT_DIR, "models", "yamnet.tflite"))
    audio_ai.start()
    
    # Biến quản lý Double Clap
    clap_count = 0
    last_clap_time = 0
    
    with open(GESTURE_MODEL_PATH, 'rb') as f:
        gesture_model = pickle.load(f)

    feature_names = [f"p{i}_{axis}" for i in range(21) for axis in ["x", "y"]]
    print("[SYSTEM] Hệ thống đã sẵn sàng")

    frame_idx = 0
    
    while True:
        now = time.time()
        state, frame, persons_bbox = yolo_ai.scan_and_display()
        if state == -1:
            print("DEBUG")
            break
        
        # --- 1. FLIP CAMERA (Lật gương) ---
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        frame_idx += 1

        if state == 1 and frame_idx % 2 == 0:
            timestamp_ms = int(time.time() * 1000)
            final_data = mp_ai.extract_hands(frame, persons_bbox, timestamp_ms)

            for track_id, data in final_data.items():
                x1, y1, x2, y2 = data["bbox"]
                nx1, nx2 = w - x2, w - x1
                cv2.rectangle(frame, (nx1, y1), (nx2, y2), (0, 255, 0), 2)

                current_frame_labels = []
                hand_positions = []
                hand_keypoints_list = [] # Lưu kp thô để tính góc

                # --- 2. NHẬN DIỆN TỪNG BÀN TAY ---
                if data["hands"]:
                    for hand_kp in data["hands"]:
                        processed_kp = preprocess_landmarks(hand_kp)
                        input_df = pd.DataFrame([processed_kp], columns=feature_names)
                        
                        # Dự đoán nhãn tức thời
                        raw_prediction = gesture_model.predict(input_df)[0]
                        current_frame_labels.append(raw_prediction)
                        hand_keypoints_list.append(hand_kp)

                        # Vẽ xương và lấy vị trí cổ tay
                        wrist_pos = draw_hand_skeleton(frame, hand_kp, w, h)
                        hand_positions.append(wrist_pos)

                        # --- GHI TÊN GESTURE LÊN ĐẦU MỖI BÀN TAY ---
                        cv2.putText(frame, raw_prediction, (wrist_pos[0], wrist_pos[1] - 20), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                current_hand_count = len(hand_positions)
                # --- LOGIC FUSION CLAP (AUDIO + VISION) ---
                # 1. Kiểm tra xem Audio có vừa nghe thấy tiếng vỗ tay không (trong 0.5s qua)
                
                if audio_ai.check_and_reset_clap():
                    # Kiểm tra Double Clap (2 cái trong vòng 1.5 giây)
                    if now - last_clap_time < 1.5:
                        clap_count += 1
                    else:
                        clap_count = 1
                    
                    last_clap_time = now
                    # print(f"--- [AUDIO AI] Vỗ tay lần {clap_count} ---")

                    if clap_count == 1:
                        send_mqtt_command("LIGHT_MODE_TOGGLE")
                        # Gửi lệnh đi ở đây
                        clap_count = 0
                        
                if now - last_clap_time > 2.0: clap_count = 0

                # --- 4. LOGIC ĐIỀU KHIỂN DỰA TRÊN TAY CHÍNH ---
                if len(current_frame_labels) > 0:
                    instant_label = current_frame_labels[0]
                    
                    # A. Fan Toggle (Palm -> Fist)
                    # if last_gesture_state == palm_label and instant_label == fist_label:
                    if (last_gesture_state in ["5-rotate", "3-three"]) and instant_label == "4-open_close":
                        send_mqtt_command("FAN_ON_OFF_TOGGLE")
                    
                    gesture_buffer.append(instant_label)
                    stable_label = collections.Counter(gesture_buffer).most_common(1)[0][0]
                        
                    # Dùng instant_label để không bị trễ bởi buffer
                    rotation_candidate_labels = ["1-one", "2-two", "3-three", "7-victory"]
                    # TÍNH GÓC XOAY CHO TAY ĐẦU TIÊN (Luôn tính để theo dõi)
                    if len(hand_keypoints_list) > 0:
                        current_angle = calculate_tilt_angle(hand_keypoints_list[0])
                        angle_diff = abs(current_angle - last_tilt_angle)
                        
                        is_rotating = False
                        # In ra để bạn debug xem góc đang là bao nhiêu
                        # print(f"[DEBUG] Label: {instant_label} | Angle: {current_angle:.2f} | Diff: {angle_diff:.2f}")

                        # CHỈ xử lý xoay nếu nhãn nằm trong danh sách "nghi vấn" xoay tay
                        if instant_label in rotation_candidate_labels and angle_diff > 30: 
                            send_mqtt_command("OSCILLATION_MODE_TOGGLE")
                            last_tilt_angle = current_angle
                            is_rotating = True
                        
                        if not is_rotating:
                            # B. Logic nhãn tĩnh (Dùng stable_label cho chuẩn)
                            if stable_label == "1-one": send_mqtt_command("SPEED_1")
                            elif stable_label == "2-two": send_mqtt_command("SPEED_2")
                            elif stable_label == "3-three": send_mqtt_command("SPEED_3")
                            elif stable_label == "7-victory": send_mqtt_command("TRACKING_ON")
                    last_gesture_state = instant_label
                    # elif stable_label == "5-rotate": send_mqtt_command("OSCILLATION_MODE")
                    # C. [FIX] LOGIC XOAY CỔ TAY (OSCILLATION)
                    # elif instant_label == "5-rotate" and len(hand_keypoints_list) > 0:
                    #     print(hand_keypoints_list)
                    #     current_angle = calculate_tilt_angle(hand_keypoints_list[0])
                        
                    #     angle_diff = abs(current_angle - last_tilt_angle)
                        
                    #     # Chỉ gửi lệnh nếu góc xoay thay đổi đáng kể (> 25 độ)
                    #     if angle_diff > 25:
                    #         send_mqtt_command("OSCILLATION_MODE_TOGGLE")
                    #         last_tilt_angle = current_angle # Cập nhật góc mới
                    # # Cập nhật trạng thái cũ
                    # last_gesture_state = instant_label
                # Hiển thị số lần vỗ tay
                cv2.putText(frame, f"Clap: {clap_count}", (nx1, y1 - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("YOLO + MediaPipe Gesture", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    yolo_ai.cleanup()
    mp_ai.cleanup()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Đã dừng chương trình.")
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")