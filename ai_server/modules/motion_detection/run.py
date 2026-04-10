# import os
# import sys
# import cv2
# import time
# import numpy as np
# import pandas as pd
# import pickle
# import collections
# import pyaudio 

# # 1. Tắt log của TensorFlow và MediaPipe thông qua biến môi trường
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'      
# os.environ['GLOG_minloglevel'] = '3'         
# os.environ['OPENCV_LOG_LEVEL'] = 'OFF'

# def silence_stderr():
#     # Mở file "hố đen"
#     devnull = os.open(os.devnull, os.O_WRONLY)
#     # Ép luồng stderr (số 2) ghi vào hố đen thay vì màn hình
#     os.dup2(devnull, 2)


# # Thiết lập đường dẫn hệ thống
# CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
# if ROOT_DIR not in sys.path:
#     sys.path.append(ROOT_DIR)

# from modules.human_detection.human_detector import HumanDetector
# from modules.motion_detection.handlers.kp_extractor import HandExtractor
# from modules.motion_detection.handlers.audio_handler import AudioClapDetector
# from modules.motion_detection.utils.hand_helpers import preprocess_landmarks, calculate_tilt_angle
# from modules.motion_detection.utils.visualizer import draw_hand_skeleton
# from modules.motion_detection.utils.logger import send_mqtt_command

# # --- CẤU HÌNH ĐƯỜNG DẪN ---
# YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8x.pt")
# GESTURE_MODEL_PATH = os.path.join(ROOT_DIR, "modules", "motion_detection", "models", "gesture_model.pkl")
# MP_MODEL_PATH = os.path.join(ROOT_DIR, "models", "gesture_recognizer.task")
# AUDIO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yamnet.tflite")

# # --- BIẾN TOÀN CỤC ---
# last_gesture_state = "none"
# gesture_buffer = collections.deque(maxlen=15) 
# clap_count = 0
# last_clap_time = 0
# last_tilt_angle = 0 
# last_sent_command = "" 

# silence_stderr()

# def main():
#     global last_gesture_state, clap_count, last_clap_time, last_tilt_angle, last_sent_command
        
#     cap = cv2.VideoCapture(0)
#     yolo_ai = HumanDetector(model_path=YOLO_MODEL_PATH, conf_threshold=0.6)
#     mp_ai = HandExtractor(mp_model=MP_MODEL_PATH)
#     audio_ai = AudioClapDetector(model_path=os.path.join(ROOT_DIR, "models", "yamnet.tflite"))
#     audio_ai.start()
    
#     # LOAD MODEL VÀ ENCODER (XGBoost version)
#     with open(GESTURE_MODEL_PATH, 'rb') as f:
#         gesture_model, label_encoder = pickle.load(f)

#     feature_names = [f"p{i}_{axis}" for i in range(21) for axis in ["x", "y"]]
#     print("[SYSTEM] Hệ thống đã sẵn sàng với XGBoost Classifier")

#     frame_idx = 0
#     prev_time = time.time()
    
#     while True:
#         now = time.time()
#         fps = 1 / (now - prev_time + 1e-6)
#         prev_time = now

#         ret, frame = cap.read()
#         if not ret: break
        
#         frame = cv2.flip(frame, 1)
#         h, w, _ = frame.shape
#         frame_idx += 1

#         # 1. YOLO chạy ngầm
#         if frame_idx % 3 == 0:
#             yolo_ai.update_frame(frame)
#         state, persons_bbox = yolo_ai.get_latest_results()

#         # 2. MediaPipe chạy ngầm
#         timestamp_ms = int(time.time() * 1000)
#         mp_ai.process_frame_async(frame, timestamp_ms)
#         latest_hands, _, _, _ = mp_ai.get_latest_results()

#         # 3. Mapping
#         final_data = {track_id: {"bbox": bbox, "hands": []} for track_id, bbox in persons_bbox.items()}
#         if latest_hands:
#             for hand_kp in latest_hands:
#                 wrist_x, wrist_y = int(hand_kp[0] * w), int(hand_kp[1] * h)
#                 actual_wrist_x = w - wrist_x 
#                 for track_id, bbox in persons_bbox.items():
#                     x1, y1, x2, y2 = bbox
#                     if x1 <= actual_wrist_x <= x2 and y1 <= wrist_y <= y2:
#                         final_data[track_id]["hands"].append(hand_kp)
#                         break
                    
#         if audio_ai.check_and_reset_clap():
#             if now - last_clap_time < 1.5: 
#                 clap_count += 1
#             else:
#                 clap_count = 1
            
#             last_clap_time = now
#             # print(f"--- [HỆ THỐNG] Nhận diện vỗ tay lần {clap_count} ---")

#             # Nếu bạn muốn vỗ 1 cái là bật luôn (như log của bạn):
#             if clap_count == 1:
#                 send_mqtt_command("LIGHT_MODE_TOGGLE")
#                 clap_count = 0 # Reset ngay sau khi gửi lệnh
        
#         # Reset clap_count nếu quá lâu không vỗ tiếp
#         if now - last_clap_time > 2.0: 
#             clap_count = 0

#         # 4. Xử lý từng người
#         for track_id, data in final_data.items():
#             x1, y1, x2, y2 = data["bbox"]
#             nx1, nx2 = w - x2, w - x1
#             cv2.rectangle(frame, (nx1, y1), (nx2, y2), (0, 255, 0), 2)

#             if data["hands"]:
#                 for hand_kp in data["hands"]:
#                     # --- DỰ ĐOÁN VỚI XÁC SUẤT (CONFIDENCE) ---
#                     processed_kp = preprocess_landmarks(hand_kp)
#                     input_df = pd.DataFrame([processed_kp], columns=feature_names)
                    
#                     # Lấy xác suất của tất cả các lớp
#                     probs = gesture_model.predict_proba(input_df)[0]
#                     max_idx = np.argmax(probs)
#                     confidence = probs[max_idx]
                    
#                     # Chỉ lấy nhãn nếu độ tin cậy > 80%
#                     if confidence > 0.80:
#                         raw_prediction = label_encoder.inverse_transform([max_idx])[0]
#                     else:
#                         raw_prediction = "none" # Không chắc chắn thì coi như không làm gì

#                     # Cập nhật buffer để Voting
#                     gesture_buffer.append(raw_prediction)
                    
#                     # --- VOTING LOGIC (BẦU CỬ) ---
#                     counts = collections.Counter(gesture_buffer)
#                     stable_label, count = counts.most_common(1)[0]
                    
#                     # Vẽ skeleton và thông tin lên màn hình
#                     wrist_pos = draw_hand_skeleton(frame, hand_kp, w, h)
#                     color = (0, 255, 0) if confidence > 0.8 else (0, 165, 255) # Cam nếu yếu
#                     cv2.putText(frame, f"{raw_prediction} ({confidence:.2f})", 
#                                 (wrist_pos[0], wrist_pos[1] - 20), 
#                                 cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

#                     # --- LOGIC ĐIỀU KHIỂN THIẾT BỊ ---
#                     # Chỉ thực hiện nếu nhãn đó ổn định (xuất hiện >= 10 lần trong 15 frame gần nhất)
#                     if count >= 10 and stable_label != "none":
                        
#                         # A. Fan Toggle (Cử chỉ chuyển động nhanh dùng instant_label)
#                         if (last_gesture_state in ["5-rotate", "3-three"]) and raw_prediction == "4-open_close":
#                             send_mqtt_command("FAN_ON_OFF_TOGGLE")
                        
#                         # B. Điều khiển tốc độ/chế độ (Dùng stable_label để tránh nhảy nhầm)
#                         if stable_label != last_sent_command:
#                             if stable_label == "1-one": send_mqtt_command("SPEED_1")
#                             elif stable_label == "2-two": send_mqtt_command("SPEED_2")
#                             elif stable_label == "3-three": send_mqtt_command("SPEED_3")
#                             elif stable_label == "7-victory": send_mqtt_command("TRACKING_ON")
#                             last_sent_command = stable_label

#                         # C. Xoay cổ tay (Tilt angle)
#                         current_angle = calculate_tilt_angle(hand_kp)
#                         angle_diff = abs(current_angle - last_tilt_angle)
#                         if stable_label in ["1-one", "2-two", "3-three"] and angle_diff > 35:
#                             send_mqtt_command("OSCILLATION_MODE_TOGGLE")
#                             last_tilt_angle = current_angle
                            
#                     last_gesture_state = raw_prediction

#                 cv2.putText(frame, f"Clap: {clap_count}", (nx1, y1 - 10), 
#                             cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

#         # Thông số hệ thống
#         cv2.putText(frame, f"FPS: {int(fps)}", (20, 40), 1, 1.5, (0, 255, 255), 2)
#         cv2.putText(frame, f"Stable: {stable_label if 'stable_label' in locals() else '...'} ({count if 'count' in locals() else 0})", 
#                     (20, 80), 1, 1.2, (255, 255, 0), 2)

#         cv2.imshow("Smart Home Pro - XGBoost + Voting", frame)
#         if cv2.waitKey(1) & 0xFF == ord('q'): break

#     cap.release()
#     yolo_ai.cleanup()
#     mp_ai.cleanup()
#     cv2.destroyAllWindows()

# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         print("Đã dừng chương trình.")
#     except Exception as e:
#         print(f"Lỗi hệ thống: {e}")

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
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

from human_detection.human_detector import HumanDetector
from motion_detection.handlers.kp_extractor import HandExtractor
from motion_detection.utils.hand_helpers import preprocess_landmarks
from motion_detection.utils.visualizer import draw_hand_skeleton
from motion_detection.utils.logger import send_mqtt_command

from motion_detection.utils.motion_utils import *
from motion_detection.handlers.gru import MotionGRU

# --- CẤU HÌNH ĐƯỜNG DẪN (Đã bỏ AUDIO_MODEL_PATH) ---
YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "motion_detection", "models", "yolov8x.pt")
GESTURE_MODEL_PATH = os.path.join(ROOT_DIR, "motion_detection", "models", "gesture_model.pkl")
MP_MODEL_PATH = os.path.join(ROOT_DIR, "motion_detection", "models", "gesture_recognizer.task")
MOTION_MODEL_PATH = os.path.join(ROOT_DIR, "motion_detection", "models", "motion_model.pth")

# silence_stderr()

# ==========================================
# CLASS QUẢN LÝ TRẠNG THÁI CHO TỪNG NGƯỜI
# ==========================================
class PersonState:
    def __init__(self):
        # Buffer cho models
        # motion buffer là cho GRU, gesture buffer là cho XGBoost
        self.motion_buffer = collections.deque(maxlen=TARGET_FRAMES)
        self.gesture_buffer = collections.deque(maxlen=15)
        
        # Trạng thái cơ bản
        self.last_gesture_state = "none"
        self.override_timer = 0

        # Hold-to-confirm (Yêu cầu giữ tư thế 1.5 giây)
        self.current_continuous_gesture = "none" 
        self.gesture_start_time = 0

        # BUFFER LƯU 30 DỰ ĐOÁN GẦN NHẤT ĐỂ ĐEM ĐI VOTING
        self.dynamic_buffer = collections.deque(maxlen=30) 

# ==========================================
# CLASS QUẢN LÝ TRẠNG THÁI CHO TỪNG NGƯỜI
# ==========================================
class PersonState:
    def __init__(self):
        # Buffer cho models
        # motion buffer là cho GRU, gesture buffer là cho XGBoost
        self.motion_buffer = collections.deque(maxlen=TARGET_FRAMES)
        self.gesture_buffer = collections.deque(maxlen=15)
        
        # Trạng thái cơ bản
        self.last_gesture_state = "none"
        self.override_timer = 0

        # Hold-to-confirm (Yêu cầu giữ tư thế 1.5 giây)
        self.current_continuous_gesture = "none" 
        self.gesture_start_time = 0

        # BUFFER LƯU 30 DỰ ĐOÁN GẦN NHẤT ĐỂ ĐEM ĐI VOTING
        self.dynamic_buffer = collections.deque(maxlen=30) 

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    print("[SYSTEM] Đang tải AI Models (Pure CV Mode)...")
    cap = cv2.VideoCapture(0)
    
    yolo_ai = HumanDetector(model_path=YOLO_MODEL_PATH, conf_threshold=0.6)
    mp_ai = HandExtractor(mp_model=MP_MODEL_PATH, max_hands=4) 
    
    motion_model = MotionGRU().to(device)
    motion_model.load_state_dict(torch.load(MOTION_MODEL_PATH, map_location=device, weights_only=True))
    motion_model.eval()

    with open(GESTURE_MODEL_PATH, 'rb') as f:
        gesture_model, label_encoder = pickle.load(f)
    feature_names = [f"p{i}_{axis}" for i in range(21) for axis in ["x", "y"]]

    print("[SYSTEM] Sẵn sàng: Multi-Person Tracking Smart Home. Bấm 'q' để thoát.")

    frame_idx = 0
    active_users = {} 
    
    # Biến UI & Cấu hình thời gian chung
    global_ui_gesture = "NONE"
    global_ui_color = (200, 200, 200)
    global_ui_timer = 0
    
    HOLD_TIME = 1.5           # Thời gian hiển thị UI
    TOGGLE_COOLDOWN = 1.5     # Thời gian "nghỉ" giữa 2 lần nhận lệnh toggle (giây)

    CONFIRM_HOLD_TIME = 1.0   # Cho static gesture

    global_cmd_cooldowns = {}

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
        # =========================================================
        current_track_ids = set(persons_bbox.keys())
        
        for old_id in list(active_users.keys()):
            if old_id not in current_track_ids:
                del active_users[old_id]
                
        for track_id in current_track_ids:
            if track_id not in active_users:
                active_users[track_id] = PersonState()

        # =========================================================
        # 2. LẶP QUA TỪNG NGƯỜI (MULTI-PERSON PROCESSING)
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
            raw_dynamic_prediction = "None"
            
            if len(user.motion_buffer) == TARGET_FRAMES:
                seq = np.array(user.motion_buffer)
                delta_seq = full_pipeline(seq) 
                input_tensor = torch.tensor(delta_seq, dtype=torch.float32).unsqueeze(0).to(device)
                
                with torch.no_grad():
                    output = motion_model(input_tensor)
                    probs = torch.softmax(output, dim=1)
                    conf, pred = torch.max(probs, 1)
                    
                    if conf.item() > 0.85: 
                        raw_dynamic_prediction = LABELS[pred.item()]

                # SLIDE WINDOW BUFFER để đự đoán tiếp cho đủ buffer
                user.motion_buffer.popleft() 

            # Lưu dự đoán thô vào Buffer của GRU
            user.dynamic_buffer.append(raw_dynamic_prediction)

            # BẦU CỬ LỌC NHIỄU CHO GRU
            dyn_counts = collections.Counter(user.dynamic_buffer)
            stable_dynamic, dyn_count = dyn_counts.most_common(1)[0]

            # XỬ LÝ LỆNH GRU
            # xỬ LÍ NHIỄU: Phải có ít nhất 20/30 frames gần nhất GRU đoán cùng 1 hành động động
            if stable_dynamic != "None" and dyn_count >= 20:
                cmd = None
                if stable_dynamic == "Clap": cmd = "Clapping"
                elif stable_dynamic == "Shake": cmd = "Shaking"

                if cmd and (now - global_cmd_cooldowns.get(cmd, 0) > TOGGLE_COOLDOWN):
                    send_mqtt_command(cmd)
                    global_cmd_cooldowns[cmd] = now
                    
                    user.override_timer = now + HOLD_TIME
                    global_ui_gesture = f"ID:{track_id} {cmd}"
                    global_ui_color = (0, 255, 255) # Màu Vàng
                    global_ui_timer = now + HOLD_TIME

                    # KÍCH HOẠT XONG: XÓA SẠCH BUFFER CỦA GRU
                    user.dynamic_buffer.clear()
                    user.motion_buffer.clear() # Xóa cả cửa sổ 50 frames để tránh đúp lệnh


            # Khóa XGBoost nếu GRU vừa gửi lệnh = now + HOLD_TIME secs
            is_overridden = (now < user.override_timer)

            # --- B. CHẠY XGBOOST CHO NGƯỜI NÀY (CỬ CHỈ TĨNH) ---
            if not is_overridden and len(user_hands) > 0:
                for hand_kp in user_hands:
                    processed_kp = preprocess_landmarks(hand_kp)
                    input_df = pd.DataFrame([processed_kp], columns=feature_names)
                    
                    probs = gesture_model.predict_proba(input_df)[0]
                    max_idx = np.argmax(probs)
                    confidence = probs[max_idx]
                    
                    raw_prediction = label_encoder.inverse_transform([max_idx])[0] if confidence > 0.85 else "none"
                    user.gesture_buffer.append(raw_prediction)
                    
                    counts = collections.Counter(user.gesture_buffer)
                    stable_label, count = counts.most_common(1)[0]

                    # HOLD-TO-CONFIRM CHỐNG NHIỄU 
                    # Phải xuất hiện 12/15 frame (rất ổn định) thì mới bắt đầu tính
                    if count >= 12 and stable_label != "none":
                        
                        # Nếu là một cử chỉ mới (hoặc vừa bị reset)
                        if user.current_continuous_gesture != stable_label:
                            user.current_continuous_gesture = stable_label
                            user.gesture_start_time = now 
                            
                        # Nếu vẫn đang giữ cử chỉ đó, kiểm tra xem đủ 1.0 giây chưa
                        elif now - user.gesture_start_time >= CONFIRM_HOLD_TIME:
                            cmd = None
                            
                            # Ánh xạ cử chỉ -> Lệnh
                            if stable_label == "1-one": cmd = "One"
                            elif stable_label == "2-two": cmd = "Two"
                            elif stable_label == "3-three": cmd = "Three"
                            elif stable_label == "7-victory": cmd = "Victory"
                            elif stable_label == "4-open_close": cmd = "Close palm" 

                            if cmd and (now - global_cmd_cooldowns.get(cmd, 0) > TOGGLE_COOLDOWN):
                                send_mqtt_command(cmd)
                                global_cmd_cooldowns[cmd] = now
                                
                                # KÍCH HOẠT XONG PHẢI RESET NGAY LẬP TỨC
                                user.current_continuous_gesture = "none"
                                user.gesture_buffer.clear()
                                
                                global_ui_gesture = f"ID:{track_id} {cmd}"
                                global_ui_color = (0, 255, 0) # Màu Xanh
                                global_ui_timer = now + HOLD_TIME
                                
                    else:
                        user.current_continuous_gesture = "none"
                            
                    user.last_gesture_state = raw_prediction
            else:
                user.gesture_buffer.append("none")
                user.current_continuous_gesture = "none"
        # =========================================================
        # 3. VẼ GIAO DIỆN (GÓC PHẢI)
        # =========================================================
        if now > global_ui_timer:
            global_ui_gesture = "NONE"
            global_ui_color = (200, 200, 200)

        cv2.putText(display_frame, f"FPS: {int(mp_fps)}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

        text_to_show = f"Last Cmd: {global_ui_gesture}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 1.0
        thickness = 3
        text_size = cv2.getTextSize(text_to_show, font, scale, thickness)[0]
        text_x = w - text_size[0] - 20 
        text_y = 40 
        
        cv2.putText(display_frame, text_to_show, (text_x, text_y), font, scale, (0,0,0), thickness+2)
        cv2.putText(display_frame, text_to_show, (text_x, text_y), font, scale, global_ui_color, thickness)

        cv2.imshow("Smart Home Camera System", display_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    # DỌN DẸP
    cap.release()
    yolo_ai.cleanup()
    mp_ai.cleanup()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()