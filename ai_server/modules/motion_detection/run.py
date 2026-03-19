import os
import sys
import cv2
import time
import numpy as np
import pandas as pd
import pickle
import collections
import torch

# 1. Tắt log
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'      
os.environ['GLOG_minloglevel'] = '3'         
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'

def silence_stderr():
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)

# Thiết lập đường dẫn
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from modules.human_detection.human_detector import HumanDetector
from modules.motion_detection.handlers.kp_extractor import HandExtractor
from modules.motion_detection.handlers.audio_handler import AudioClapDetector
from modules.motion_detection.utils.hand_helpers import preprocess_landmarks
from modules.motion_detection.utils.visualizer import draw_hand_skeleton
from modules.motion_detection.utils.logger import send_mqtt_command

from modules.motion_detection.utils.motion_utils import *
from modules.motion_detection.handlers.gru import MotionGRU

# --- CẤU HÌNH ĐƯỜNG DẪN ---
YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8x.pt")
GESTURE_MODEL_PATH = os.path.join(ROOT_DIR, "modules", "motion_detection", "models", "gesture_model.pkl")
MP_MODEL_PATH = os.path.join(ROOT_DIR, "models", "gesture_recognizer.task")
AUDIO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yamnet.tflite")
MOTION_MODEL_PATH = os.path.join(ROOT_DIR, "modules", "motion_detection", "models", "motion_model.pth")

silence_stderr()

# ==========================================
# CLASS QUẢN LÝ TRẠNG THÁI CHO TỪNG NGƯỜI
# ==========================================
class PersonState:
    def __init__(self):
        self.motion_buffer = collections.deque(maxlen=TARGET_FRAMES)
        self.gesture_buffer = collections.deque(maxlen=15)
        self.last_gesture_state = "none"
        self.last_sent_command = ""
        self.override_timer = 0
        self.held_dynamic_action = "NONE"

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    print("[SYSTEM] Đang tải AI Models...")
    cap = cv2.VideoCapture(1)
    yolo_ai = HumanDetector(model_path=YOLO_MODEL_PATH, conf_threshold=0.6)
    
    # LƯU Ý: Tăng max_hands lên 4 hoặc 6 để bắt được tay của 2-3 người cùng lúc
    mp_ai = HandExtractor(mp_model=MP_MODEL_PATH, max_hands=4) 

    audio_ai = AudioClapDetector(model_path=AUDIO_MODEL_PATH)
    audio_ai.start()
    
    motion_model = MotionGRU().to(device)
    motion_model.load_state_dict(torch.load(MOTION_MODEL_PATH, map_location=device, weights_only=True))
    motion_model.eval()

    with open(GESTURE_MODEL_PATH, 'rb') as f:
        gesture_model, label_encoder = pickle.load(f)
    feature_names = [f"p{i}_{axis}" for i in range(21) for axis in ["x", "y"]]

    print("[SYSTEM] Sẵn sàng: Multi-Person Tracking Smart Home. Bấm 'q' để thoát.")

    frame_idx = 0
    
    # --- TỪ ĐIỂN LƯU TRẠNG THÁI CỦA MỌI NGƯỜI TRONG PHÒNG ---
    # Key: track_id (int), Value: PersonState object
    active_users = {} 
    
    # Biến quản lý Audio Clap chung cho cả phòng
    global_clap_count = 0
    global_last_clap_time = 0

    # Biến để vẽ Giao diện góc phải (Luôn ưu tiên hiển thị lệnh mới nhất của bất kỳ ai)
    global_ui_gesture = "NONE"
    global_ui_color = (200, 200, 200)
    global_ui_timer = 0
    HOLD_TIME = 0.5 

    while cap.isOpened():
        now = time.time()
        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        frame_idx += 1

        if frame_idx % 3 == 0:
            yolo_ai.update_frame(frame)
        state, persons_bbox = yolo_ai.get_latest_results()

        timestamp_ms = int(now * 1000)
        mp_ai.process_frame_async(frame, timestamp_ms)
        latest_hands, _, mp_frame, mp_fps = mp_ai.get_latest_results()
        
        display_frame = mp_frame if mp_frame is not None else frame.copy()

        # =========================================================
        # 1. QUẢN LÝ TRACK ID & GARBAGE COLLECTION
        # ==========================================
        current_track_ids = set(persons_bbox.keys())
        
        # Xóa những người đã đi ra khỏi camera để giải phóng RAM
        for old_id in list(active_users.keys()):
            if old_id not in current_track_ids:
                del active_users[old_id]
                
        # Thêm người mới vào hệ thống
        for track_id in current_track_ids:
            if track_id not in active_users:
                active_users[track_id] = PersonState()

        # =========================================================
        # 2. XỬ LÝ ÂM THANH (AUDIO CLAP - CHUNG CHO CẢ PHÒNG)
        # =========================================================
        is_audio_clap = audio_ai.check_and_reset_clap()
        if is_audio_clap:
            if now - global_last_clap_time < 1.5: global_clap_count += 1
            else: global_clap_count = 1
            global_last_clap_time = now

            if global_clap_count == 2:
                send_mqtt_command("LIGHT_MODE_TOGGLE")
                global_clap_count = 0
                # Cập nhật UI chung
                global_ui_gesture = "AUDIO CLAP"
                global_ui_color = (0, 165, 255) # Cam
                global_ui_timer = now + HOLD_TIME
                
        if now - global_last_clap_time > 2.0: global_clap_count = 0


        # =========================================================
        # 3. LẶP QUA TỪNG NGƯỜI (MULTI-PERSON PROCESSING)
        # =========================================================
        for track_id, bbox in persons_bbox.items():
            user = active_users[track_id]
            px1, py1, px2, py2 = bbox
            cv2.rectangle(display_frame, (px1, py1), (px2, py2), (0, 255, 0), 2)
            cv2.putText(display_frame, f"ID:{track_id}", (px1, py1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Lọc và sắp xếp tay cho user này
            user_hands = []
            if latest_hands:
                for hand_kp in latest_hands:
                    wrist_x, wrist_y = int(hand_kp[0] * w), int(hand_kp[1] * h)
                    if px1 <= wrist_x <= px2 and py1 <= wrist_y <= py2:
                        user_hands.append(hand_kp)
                        draw_hand_skeleton(display_frame, hand_kp, w, h)

            # Khởi tạo data cho GRU
            gru_frame_keypoints = np.full(126, MISSING_VALUE)
            if len(user_hands) > 0:
                user_hands.sort(key=lambda kp: kp[0]) # Sắp xếp Trái -> Phải
                for i, hand_kp in enumerate(user_hands[:2]):
                    gru_frame_keypoints[i*63 : (i+1)*63] = hand_kp
                    
            user.motion_buffer.append(gru_frame_keypoints)

            # --- A. CHẠY GRU CHO NGƯỜI NÀY ---
            dynamic_gesture = "None"
            if len(user.motion_buffer) == TARGET_FRAMES:
                seq = np.array(user.motion_buffer)
                delta_seq = full_pipeline(seq) 
                input_tensor = torch.tensor(delta_seq, dtype=torch.float32).unsqueeze(0).to(device)
                
                with torch.no_grad():
                    output = motion_model(input_tensor)
                    probs = torch.softmax(output, dim=1)
                    conf, pred = torch.max(probs, 1)
                    
                    if conf.item() > 0.80: 
                        detected_action = LABELS[pred.item()]
                        if detected_action != "None":
                            dynamic_gesture = detected_action
                            user.motion_buffer.clear() 
                        else:
                            user.motion_buffer.popleft() 
                    else:
                        user.motion_buffer.popleft() 

            # Xử lý lệnh GRU
            if dynamic_gesture == "Clap":
                send_mqtt_command("LIGHT_MODE_TOGGLE")
                user.override_timer = now + HOLD_TIME
                global_ui_gesture = f"ID:{track_id} CLAP"
                global_ui_color = (0, 255, 255)
                global_ui_timer = now + HOLD_TIME
                user.gesture_buffer.clear()
                
            elif dynamic_gesture == "Shake":
                send_mqtt_command("OSCILLATION_MODE_TOGGLE")
                user.override_timer = now + HOLD_TIME
                global_ui_gesture = f"ID:{track_id} SHAKE"
                global_ui_color = (0, 255, 255)
                global_ui_timer = now + HOLD_TIME
                user.gesture_buffer.clear()

            is_overridden = (now < user.override_timer)

            # --- B. CHẠY XGBOOST CHO NGƯỜI NÀY (Nếu ko bị GRU khóa) ---
            if not is_overridden and len(user_hands) > 0:
                for hand_kp in user_hands:
                    processed_kp = preprocess_landmarks(hand_kp)
                    input_df = pd.DataFrame([processed_kp], columns=feature_names)
                    
                    probs = gesture_model.predict_proba(input_df)[0]
                    max_idx = np.argmax(probs)
                    confidence = probs[max_idx]
                    
                    raw_prediction = label_encoder.inverse_transform([max_idx])[0] if confidence > 0.80 else "none"
                    user.gesture_buffer.append(raw_prediction)
                    
                    counts = collections.Counter(user.gesture_buffer)
                    stable_label, count = counts.most_common(1)[0]

                    if count >= 10 and stable_label != "none":
                        if (user.last_gesture_state in ["5-rotate", "3-three"]) and raw_prediction == "4-open_close":
                            send_mqtt_command("FAN_ON_OFF_TOGGLE")
                            user.gesture_buffer.clear() 
                        
                        if stable_label != user.last_sent_command:
                            if stable_label == "1-one": send_mqtt_command("SPEED_1")
                            elif stable_label == "2-two": send_mqtt_command("SPEED_2")
                            elif stable_label == "3-three": send_mqtt_command("SPEED_3")
                            elif stable_label == "7-victory": send_mqtt_command("TRACKING_ON")
                            user.last_sent_command = stable_label
                            
                            # Cập nhật UI chung
                            global_ui_gesture = f"ID:{track_id} {stable_label.upper()}"
                            global_ui_color = (0, 255, 0)
                            global_ui_timer = now + HOLD_TIME
                            
                    user.last_gesture_state = raw_prediction

        # =========================================================
        # 4. VẼ GIAO DIỆN (GÓC PHẢI TỔNG HỢP)
        # =========================================================
        if now > global_ui_timer:
            global_ui_gesture = "NONE"
            global_ui_color = (200, 200, 200)

        cv2.putText(display_frame, f"FPS: {int(mp_fps)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
        cv2.putText(display_frame, f"Audio Claps: {global_clap_count}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        text_to_show = f"Last Cmd: {global_ui_gesture}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1.0
        thickness = 3
        text_size = cv2.getTextSize(text_to_show, font, scale, thickness)[0]
        text_x = w - text_size[0] - 20 
        text_y = 40 
        
        cv2.putText(display_frame, text_to_show, (text_x, text_y), font, scale, (0,0,0), thickness+2)
        cv2.putText(display_frame, text_to_show, (text_x, text_y), font, scale, global_ui_color, thickness)

        cv2.imshow("Smart Home Pro - Multi-Person AI", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    # DỌN DẸP
    cap.release()
    yolo_ai.cleanup()
    mp_ai.cleanup()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()