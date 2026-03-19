import cv2
import numpy as np
import mediapipe as mp
import time

class HandExtractor:
    def __init__(self, mp_model='models/gesture_recognizer.task', max_hands=6):
        print("[MODULE_HAND_POSE] Đang khởi tạo MediaPipe (LIVE_STREAM)...")
        self.latest_hands = [] 
        self.latest_gestures = []
        
        # BIẾN LƯU FRAME VÀ FPS CỦA MEDIAPIPE
        self.latest_frame = None 
        self.mp_prev_time = time.time()
        self.mp_fps = 0
        
        BaseOptions = mp.tasks.BaseOptions
        GestureRecognizer = mp.tasks.vision.GestureRecognizer
        GestureRecognizerOptions = mp.tasks.vision.GestureRecognizerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode

        options = GestureRecognizerOptions(
            base_options=BaseOptions(model_asset_path=mp_model),
            running_mode=VisionRunningMode.LIVE_STREAM,
            num_hands=max_hands,
            result_callback=self._result_callback       
        )
        self.recognizer = GestureRecognizer.create_from_options(options)

    def _result_callback(self, result: mp.tasks.vision.GestureRecognizerResult, output_image: mp.Image, timestamp_ms: int):
        extracted_hands = []
        gestures = []
        
        if result.hand_landmarks:
            for hand_landmarks in result.hand_landmarks:
                kp_array = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks]).flatten()
                extracted_hands.append(kp_array)
                
        if result.gestures:
            for gesture_list in result.gestures:
                if len(gesture_list) > 0:
                    gestures.append(gesture_list[0].category_name)
        
        # 1. Trích xuất frame chuẩn từ MediaPipe (Nó trả về RGB, ta phải đổi lại thành BGR để cv2.imshow)
        frame_rgb = output_image.numpy_view()
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        
        # 2. Tính toán FPS thực tế của MediaPipe
        current_time = time.time()
        fps = 1 / (current_time - self.mp_prev_time) if (current_time - self.mp_prev_time) > 0 else 0
        self.mp_prev_time = current_time

        # 3. Cập nhật dữ liệu
        self.latest_hands = extracted_hands
        self.latest_gestures = gestures
        self.latest_frame = frame_bgr
        self.mp_fps = int(fps)

    def process_frame_async(self, frame, timestamp_ms):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        self.recognizer.recognize_async(mp_image, timestamp_ms)

    def get_latest_results(self):
        # Hàm này giờ trả về cả frame và fps
        return self.latest_hands, self.latest_gestures, self.latest_frame, self.mp_fps

    def cleanup(self):
        self.recognizer.close()
        print("[MODULE_HAND_POSE] Đã giải phóng tài nguyên MediaPipe.")