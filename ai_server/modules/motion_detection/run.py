import os
import sys
import cv2
import time
import pandas as pd
import pickle
import collections
import pyaudio 

# 1. Tắt log của TensorFlow và MediaPipe thông qua biến môi trường
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'      
os.environ['GLOG_minloglevel'] = '3'         
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'

def silence_stderr():
    # Mở file "hố đen"
    devnull = os.open(os.devnull, os.O_WRONLY)
    # Ép luồng stderr (số 2) ghi vào hố đen thay vì màn hình
    os.dup2(devnull, 2)


# Thiết lập đường dẫn hệ thống
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from modules.human_detection.human_detector import HumanDetector
from modules.motion_detection.handlers.kp_extractor import HandExtractor
from modules.motion_detection.handlers.audio_handler import AudioClapDetector
from modules.motion_detection.utils.hand_helpers import preprocess_landmarks, calculate_tilt_angle
from modules.motion_detection.utils.visualizer import draw_hand_skeleton
from modules.motion_detection.utils.logger import send_mqtt_command

# --- CẤU HÌNH ĐƯỜNG DẪN ---
YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8n.pt")
GESTURE_MODEL_PATH = os.path.join(ROOT_DIR, "modules", "motion_detection", "models", "gesture_model.pkl")
MP_MODEL_PATH = os.path.join(ROOT_DIR, "models", "gesture_recognizer.task")
AUDIO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yamnet.tflite")

# --- BIẾN TOÀN CỤC ---
last_gesture_state = "none"
gesture_buffer = collections.deque(maxlen=5) 
clap_count = 0
last_clap_time = 0
last_tilt_angle = 0 

silence_stderr()

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
                # --- LOGIC FUSION CLAP  ---
                if audio_ai.check_and_reset_clap():
                    # Kiểm tra Double Clap (2 cái trong vòng 1.5 giây)
                    if now - last_clap_time < 1.5:
                        clap_count += 1
                    else:
                        clap_count = 1
                    
                    last_clap_time = now

                    if clap_count == 1:
                        send_mqtt_command("LIGHT_MODE_TOGGLE")
                        # Gửi lệnh đi ở đây
                        clap_count = 0
                        
                if now - last_clap_time > 2.0: clap_count = 0

                # --- 4. LOGIC ĐIỀU KHIỂN DỰA TRÊN TAY CHÍNH ---
                if len(current_frame_labels) > 0:
                    instant_label = current_frame_labels[0]
                    
                    # A. Fan Toggle (Palm -> Fist)
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