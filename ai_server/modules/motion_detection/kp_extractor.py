import cv2
import numpy as np
import mediapipe as mp

class HandExtractor:
    def __init__(self, mp_model='gesture_recognizer.task'):
        print("[MODULE_HAND_POSE] Đang khởi tạo MediaPipe...")
        BaseOptions = mp.tasks.BaseOptions
        GestureRecognizer = mp.tasks.vision.GestureRecognizer
        GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = GestureRecognizerOptions(
            base_options=BaseOptions(model_asset_path=mp_model),
            running_mode=VisionRunningMode.VIDEO, 
            num_hands=4 
        )
        self.recognizer = GestureRecognizer.create_from_options(options)

    def extract_hands(self, frame, persons_bbox, timestamp_ms):
        """Nhận frame và dictionary bboxes từ YOLO, trả về keypoint tương ứng"""
        h, w, _ = frame.shape
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)

        gesture_result = self.recognizer.recognize_for_video(mp_image, timestamp_ms)

        # Khởi tạo sườn dữ liệu
        extracted_data = {track_id: {"bbox": bbox, "hands": []} for track_id, bbox in persons_bbox.items()}

        if gesture_result.hand_landmarks:
            for hand_landmarks in gesture_result.hand_landmarks:
                wrist = hand_landmarks[0]
                wx, wy = int(wrist.x * w), int(wrist.y * h)

                for track_id, bbox in persons_bbox.items():
                    x1, y1, x2, y2 = bbox
                    if x1 <= wx <= x2 and y1 <= wy <= y2:
                        kp_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks]).flatten()
                        extracted_data[track_id]["hands"].append(kp_array)
                        break 

        return extracted_data

    def cleanup(self):
        self.recognizer.close()
        print("[MODULE_HAND_POSE] Đã giải phóng tài nguyên MediaPipe.")