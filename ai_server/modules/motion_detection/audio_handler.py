import mediapipe as mp
import numpy as np
import time
import threading
import pyaudio
from mediapipe.tasks import python
from mediapipe.tasks.python import audio
from mediapipe.tasks.python.audio import AudioClassifierOptions, RunningMode, AudioClassifierResult
AudioData = mp.tasks.components.containers.AudioData

class AudioClapDetector:
    def __init__(self, model_path):
        self.model_path = model_path
        self.is_clap_detected = False
        self.last_detection_time = 0
        
        # Cấu hình âm thanh
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000  # YamNet yêu cầu 16kHz
        self.chunk = 8000   # Lấy mẫu mỗi 0.5 giây
        self.current_timestamp_ms = 0
        
        # Khởi tạo MediaPipe Audio Classifier
        base_options = python.BaseOptions(model_asset_path=self.model_path)
        options = AudioClassifierOptions(
            base_options=base_options,
            running_mode=RunningMode.AUDIO_STREAM,
            max_results=1,
            result_callback=self._audio_callback
        )
        self.classifier = audio.AudioClassifier.create_from_options(options)
        self.pa = pyaudio.PyAudio()

    def _audio_callback(self, result: AudioClassifierResult, timestamp_ms: int):
        """Hàm này chạy mỗi khi AI nhận diện xong 1 đoạn âm thanh"""
        if result.classifications:
            category = result.classifications[0].categories[0]
            if category.category_name == "Hands" and category.score > 0.4:
                self.is_clap_detected = True
                self.last_detection_time = time.time()
                print(f"[DEBUG AUDIO] Detect Clap! Score: {category.score:.2f}")

    def _listen(self):
        stream = self.pa.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        print("[AUDIO] Bắt đầu nghe tiếng vỗ tay (streaming mode)...")
        
        while True:
            try:
                data = stream.read(self.chunk, exception_on_overflow=False)
                raw_audio = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                
                audio_clip = AudioData.create_from_array(
                    raw_audio,
                    sample_rate=self.rate
                )
                num_samples = len(raw_audio)
                timestamp_increment_ms = int((num_samples / self.rate) * 1000)
                self.current_timestamp_ms += timestamp_increment_ms
                
                # KHÔNG gọi classify() nữa
                self.classifier.classify_async(
                    audio_clip,
                    timestamp_ms=self.current_timestamp_ms 
                )
                
            except Exception as e:
                print(f"Audio Thread Error: {e}")
                time.sleep(0.1)


    def start(self):
        """Khởi động luồng nghe"""
        thread = threading.Thread(target=self._listen, daemon=True)
        thread.start()

    def check_and_reset_clap(self):
        """Hàm để luồng chính (Camera) kiểm tra xem có tiếng vỗ tay không"""
        if self.is_clap_detected:
            self.is_clap_detected = False
            return True
        return False