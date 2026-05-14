import os
import sys
import cv2
import time
import numpy as np
import pandas as pd
import pickle
import collections
import torch
from Adafruit_IO import MQTTClient
from dotenv import load_dotenv

load_dotenv()

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'      
os.environ['GLOG_minloglevel'] = '3'         
os.environ['OPENCV_LOG_LEVEL'] = 'OFF'

from modules.human_detection.human_detector import HumanDetector
from modules.motion_detection.handlers.kp_extractor import HandExtractor
from modules.motion_detection.utils.hand_helpers import preprocess_landmarks
from modules.motion_detection.utils.visualizer import draw_hand_skeleton
from modules.motion_detection.utils.logger import send_mqtt_command, connect_mqtt
from modules.motion_detection.utils.motion_utils import *
from modules.motion_detection.handlers.gru import MotionGRU
from database.db_manager import DatabaseManager

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = CURRENT_DIR

YOLO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yolov8x.pt")
GESTURE_MODEL_PATH = os.path.join(ROOT_DIR, "modules", "motion_detection", "models", "gesture_model.pkl")
MP_MODEL_PATH = os.path.join(ROOT_DIR, "models", "gesture_recognizer.task")
MOTION_MODEL_PATH = os.path.join(ROOT_DIR, "modules", "motion_detection", "models", "motion_model.pth")

AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")

current_temp = 0
current_light = 0
threshold_temp = 30.0
threshold_light = 100.0
db = DatabaseManager()

def connected(client):
    print("[MQTT] Kết nối thành công tới Adafruit IO ...")
    client.subscribe("human-detect-pir") 
    client.subscribe("env-temp") 
    client.subscribe("env-light")

def disconnected(client):
    print("[MQTT] Đã ngắt kết nối ... ")
    try:
        client.connect()
    except Exception as e:
        print("Reconnect lỗi:", e)

def message(client, feed_id, payload):
    global current_temp, current_light, threshold_temp, threshold_light
    try:
        val = float(payload)
        if feed_id == "human-detect-pir":
            db.log_sensor("PIR", val)
            print(f"[MQTT] PIR status: {val}")
        elif feed_id == "env-temp":
            current_temp = val
            db.log_sensor("TEMP", val)
        elif feed_id == "env-light":
            current_light = val
            db.log_sensor("LIGHT", val)
    except Exception as e:
        print(f"Lỗi nhận tin: {e}")

class PersonState:
    def __init__(self):
        self.motion_buffer = collections.deque(maxlen=TARGET_FRAMES)
        self.gesture_buffer = collections.deque(maxlen=15)
        self.last_gesture_state = "none"
        self.override_timer = 0
        self.current_continuous_gesture = "none" 
        self.gesture_start_time = 0
        self.dynamic_buffer = collections.deque(maxlen=30) 

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
    print("[SYSTEM] Đang tải AI Models...")
    cap = cv2.VideoCapture(0)
    
    yolo_ai = HumanDetector(model_path=YOLO_MODEL_PATH, conf_threshold=0.6)
    mp_ai = HandExtractor(mp_model=MP_MODEL_PATH, max_hands=4) 
    
    motion_model = MotionGRU().to(device)
    motion_model.load_state_dict(torch.load(MOTION_MODEL_PATH, map_location=device, weights_only=True))
    motion_model.eval()

    with open(GESTURE_MODEL_PATH, 'rb') as f:
        gesture_model, label_encoder = pickle.load(f)
    feature_names = [f"p{i}_{axis}" for i in range(21) for axis in ["x", "y"]]

    print("[SYSTEM] Kết nối MQTT...")
    mqtt_client = MQTTClient(AIO_USERNAME, AIO_KEY)
    mqtt_client.on_connect = connected
    mqtt_client.on_disconnect = disconnected
    mqtt_client.on_message = message
    try:
        mqtt_client.connect()
        mqtt_client.loop_background()
        time.sleep(2)
    except Exception as e:
        print(f"[MQTT_ERROR] Không thể kết nối đến server Adafruit: {e}")

    connect_mqtt()

    print("[SYSTEM] Sẵn sàng: Multi-Person Tracking Smart Home. Bấm 'q' để thoát.")

    frame_idx = 0
    active_users = {} 
    
    global_ui_gesture = "NONE"
    global_ui_color = (200, 200, 200)
    global_ui_timer = 0
    
    HOLD_TIME = 1.5
    TOGGLE_COOLDOWN = 1.5
    CONFIRM_HOLD_TIME = 1.0

    global_cmd_cooldowns = {}

    last_state = -1
    mqtt_last_time = time.time()
    last_seen_time = time.time() 
    DELAY_TURN_OFF = 3.0          
    UPDATE_TIME = 10.0            

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

        current_track_ids = set(persons_bbox.keys())
        
        for old_id in list(active_users.keys()):
            if old_id not in current_track_ids:
                del active_users[old_id]
                
        for track_id in current_track_ids:
            if track_id not in active_users:
                active_users[track_id] = PersonState()

        for track_id, bbox in persons_bbox.items():
            user = active_users[track_id]
            px1, py1, px2, py2 = bbox
            cv2.rectangle(display_frame, (px1, py1), (px2, py2), (0, 255, 0), 2)
            cv2.putText(display_frame, f"ID:{track_id}", (px1, py1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            user_hands = []
            if latest_hands:
                for hand_kp in latest_hands:
                    wrist_x, wrist_y = int(hand_kp[0] * w), int(hand_kp[1] * h)
                    if px1 <= wrist_x <= px2 and py1 <= wrist_y <= py2:
                        user_hands.append(hand_kp)
                        draw_hand_skeleton(display_frame, hand_kp, w, h)

            gru_frame_keypoints = np.full(126, MISSING_VALUE)
            if len(user_hands) > 0:
                user_hands.sort(key=lambda kp: kp[0])
                for i, hand_kp in enumerate(user_hands[:2]):
                    gru_frame_keypoints[i*63 : (i+1)*63] = hand_kp
                    
            user.motion_buffer.append(gru_frame_keypoints)

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

                user.motion_buffer.popleft() 

            user.dynamic_buffer.append(raw_dynamic_prediction)

            dyn_counts = collections.Counter(user.dynamic_buffer)
            stable_dynamic, dyn_count = dyn_counts.most_common(1)[0]

            if stable_dynamic != "None" and dyn_count >= 20:
                cmd = None
                if stable_dynamic == "Clap": cmd = "Clapping"
                elif stable_dynamic == "Shake": cmd = "Shaking"

                if cmd and (now - global_cmd_cooldowns.get(cmd, 0) > TOGGLE_COOLDOWN):
                    send_mqtt_command(cmd)
                    global_cmd_cooldowns[cmd] = now
                    
                    user.override_timer = now + HOLD_TIME
                    global_ui_gesture = f"ID:{track_id} {cmd}"
                    global_ui_color = (0, 255, 255)
                    global_ui_timer = now + HOLD_TIME

                    user.dynamic_buffer.clear()
                    user.motion_buffer.clear()

            is_overridden = (now < user.override_timer)

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

                    if count >= 12 and stable_label != "none":
                        
                        if user.current_continuous_gesture != stable_label:
                            user.current_continuous_gesture = stable_label
                            user.gesture_start_time = now 
                            
                        elif now - user.gesture_start_time >= CONFIRM_HOLD_TIME:
                            cmd = None
                            
                            if stable_label == "1-one": cmd = "One"
                            elif stable_label == "2-two": cmd = "Two"
                            elif stable_label == "3-three": cmd = "Three"
                            elif stable_label == "7-victory": cmd = "Victory"
                            elif stable_label == "4-open_close": cmd = "Close palm" 

                            if cmd and (now - global_cmd_cooldowns.get(cmd, 0) > TOGGLE_COOLDOWN):
                                send_mqtt_command(cmd)
                                global_cmd_cooldowns[cmd] = now
                                
                                user.current_continuous_gesture = "none"
                                user.gesture_buffer.clear()
                                
                                global_ui_gesture = f"ID:{track_id} {cmd}"
                                global_ui_color = (0, 255, 0)
                                global_ui_timer = now + HOLD_TIME
                                
                    else:
                        user.current_continuous_gesture = "none"
                            
                    user.last_gesture_state = raw_prediction
            else:
                user.gesture_buffer.append("none")
                user.current_continuous_gesture = "none"

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

    cap.release()
    yolo_ai.cleanup()
    mp_ai.cleanup()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
