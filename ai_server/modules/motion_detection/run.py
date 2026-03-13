import os
import sys
import cv2
import time
import numpy as np
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
YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8x.pt")
GESTURE_MODEL_PATH = os.path.join(ROOT_DIR, "modules", "motion_detection", "models", "gesture_model.pkl")
MP_MODEL_PATH = os.path.join(ROOT_DIR, "models", "gesture_recognizer.task")
AUDIO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yamnet.tflite")

# --- BIẾN TOÀN CỤC ---
last_gesture_state = "none"
gesture_buffer = collections.deque(maxlen=15) 
clap_count = 0
last_clap_time = 0
last_tilt_angle = 0 
last_sent_command = "" 

silence_stderr()

def main():
    global last_gesture_state, clap_count, last_clap_time, last_tilt_angle, last_sent_command
        
    cap = cv2.VideoCapture(0)
    yolo_ai = HumanDetector(model_path=YOLO_MODEL_PATH, conf_threshold=0.6)
    mp_ai = HandExtractor(mp_model=MP_MODEL_PATH)
    audio_ai = AudioClapDetector(model_path=os.path.join(ROOT_DIR, "models", "yamnet.tflite"))
    audio_ai.start()
    
    # LOAD MODEL VÀ ENCODER (XGBoost version)
    with open(GESTURE_MODEL_PATH, 'rb') as f:
        gesture_model, label_encoder = pickle.load(f)

    feature_names = [f"p{i}_{axis}" for i in range(21) for axis in ["x", "y"]]
    print("[SYSTEM] Hệ thống đã sẵn sàng với XGBoost Classifier")

    frame_idx = 0
    prev_time = time.time()
    
    while True:
        now = time.time()
        fps = 1 / (now - prev_time + 1e-6)
        prev_time = now

        ret, frame = cap.read()
        if not ret: break
        
        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        frame_idx += 1

        # 1. YOLO chạy ngầm
        if frame_idx % 3 == 0:
            yolo_ai.update_frame(frame)
        state, persons_bbox = yolo_ai.get_latest_results()

        # 2. MediaPipe chạy ngầm
        timestamp_ms = int(time.time() * 1000)
        mp_ai.process_frame_async(frame, timestamp_ms)
        latest_hands, _, _, _ = mp_ai.get_latest_results()

        # 3. Mapping
        final_data = {track_id: {"bbox": bbox, "hands": []} for track_id, bbox in persons_bbox.items()}
        if latest_hands:
            for hand_kp in latest_hands:
                wrist_x, wrist_y = int(hand_kp[0] * w), int(hand_kp[1] * h)
                actual_wrist_x = w - wrist_x 
                for track_id, bbox in persons_bbox.items():
                    x1, y1, x2, y2 = bbox
                    if x1 <= actual_wrist_x <= x2 and y1 <= wrist_y <= y2:
                        final_data[track_id]["hands"].append(hand_kp)
                        break
                    
        if audio_ai.check_and_reset_clap():
            if now - last_clap_time < 1.5: 
                clap_count += 1
            else:
                clap_count = 1
            
            last_clap_time = now
            # print(f"--- [HỆ THỐNG] Nhận diện vỗ tay lần {clap_count} ---")

            # Nếu bạn muốn vỗ 1 cái là bật luôn (như log của bạn):
            if clap_count == 1:
                send_mqtt_command("LIGHT_MODE_TOGGLE")
                clap_count = 0 # Reset ngay sau khi gửi lệnh
        
        # Reset clap_count nếu quá lâu không vỗ tiếp
        if now - last_clap_time > 2.0: 
            clap_count = 0

        # 4. Xử lý từng người
        for track_id, data in final_data.items():
            x1, y1, x2, y2 = data["bbox"]
            nx1, nx2 = w - x2, w - x1
            cv2.rectangle(frame, (nx1, y1), (nx2, y2), (0, 255, 0), 2)

            if data["hands"]:
                for hand_kp in data["hands"]:
                    # --- DỰ ĐOÁN VỚI XÁC SUẤT (CONFIDENCE) ---
                    processed_kp = preprocess_landmarks(hand_kp)
                    input_df = pd.DataFrame([processed_kp], columns=feature_names)
                    
                    # Lấy xác suất của tất cả các lớp
                    probs = gesture_model.predict_proba(input_df)[0]
                    max_idx = np.argmax(probs)
                    confidence = probs[max_idx]
                    
                    # Chỉ lấy nhãn nếu độ tin cậy > 80%
                    if confidence > 0.80:
                        raw_prediction = label_encoder.inverse_transform([max_idx])[0]
                    else:
                        raw_prediction = "none" # Không chắc chắn thì coi như không làm gì

                    # Cập nhật buffer để Voting
                    gesture_buffer.append(raw_prediction)
                    
                    # --- VOTING LOGIC (BẦU CỬ) ---
                    counts = collections.Counter(gesture_buffer)
                    stable_label, count = counts.most_common(1)[0]
                    
                    # Vẽ skeleton và thông tin lên màn hình
                    wrist_pos = draw_hand_skeleton(frame, hand_kp, w, h)
                    color = (0, 255, 0) if confidence > 0.8 else (0, 165, 255) # Cam nếu yếu
                    cv2.putText(frame, f"{raw_prediction} ({confidence:.2f})", 
                                (wrist_pos[0], wrist_pos[1] - 20), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    # --- LOGIC ĐIỀU KHIỂN THIẾT BỊ ---
                    # Chỉ thực hiện nếu nhãn đó ổn định (xuất hiện >= 10 lần trong 15 frame gần nhất)
                    if count >= 10 and stable_label != "none":
                        
                        # A. Fan Toggle (Cử chỉ chuyển động nhanh dùng instant_label)
                        if (last_gesture_state in ["5-rotate", "3-three"]) and raw_prediction == "4-open_close":
                            send_mqtt_command("FAN_ON_OFF_TOGGLE")
                        
                        # B. Điều khiển tốc độ/chế độ (Dùng stable_label để tránh nhảy nhầm)
                        if stable_label != last_sent_command:
                            if stable_label == "1-one": send_mqtt_command("SPEED_1")
                            elif stable_label == "2-two": send_mqtt_command("SPEED_2")
                            elif stable_label == "3-three": send_mqtt_command("SPEED_3")
                            elif stable_label == "7-victory": send_mqtt_command("TRACKING_ON")
                            last_sent_command = stable_label

                        # C. Xoay cổ tay (Tilt angle)
                        current_angle = calculate_tilt_angle(hand_kp)
                        angle_diff = abs(current_angle - last_tilt_angle)
                        if stable_label in ["1-one", "2-two", "3-three"] and angle_diff > 35:
                            send_mqtt_command("OSCILLATION_MODE_TOGGLE")
                            last_tilt_angle = current_angle
                            
                    last_gesture_state = raw_prediction

                cv2.putText(frame, f"Clap: {clap_count}", (nx1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Thông số hệ thống
        cv2.putText(frame, f"FPS: {int(fps)}", (20, 40), 1, 1.5, (0, 255, 255), 2)
        cv2.putText(frame, f"Stable: {stable_label if 'stable_label' in locals() else '...'} ({count if 'count' in locals() else 0})", 
                    (20, 80), 1, 1.2, (255, 255, 0), 2)

        cv2.imshow("Smart Home Pro - XGBoost + Voting", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'): break

    cap.release()
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