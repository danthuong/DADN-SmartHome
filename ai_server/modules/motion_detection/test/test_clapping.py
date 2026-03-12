import os
# Tắt log của TensorFlow (0: Tất cả, 1: Tắt INFO, 2: Tắt INFO+WARN, 3: Tắt tất cả lỗi)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
# Tắt log của MediaPipe (GLOG)
os.environ['GLOG_minloglevel'] = '2' 
import sys
import numpy as np
import pyaudio
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import audio
from mediapipe.tasks.python.components.containers import audio_data


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../../"))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

AUDIO_MODEL_PATH = os.path.join(ROOT_DIR, "models", "yamnet.tflite")  # đường dẫn model

# cấu hình mic
RATE = 16000
CHUNK = 8000
CHANNELS = 1

# tạo classifier
base_options = python.BaseOptions(model_asset_path=AUDIO_MODEL_PATH)

options = audio.AudioClassifierOptions(
    base_options=base_options,
    running_mode=audio.RunningMode.AUDIO_CLIPS,
    max_results=3
)

classifier = audio.AudioClassifier.create_from_options(options)

# mở mic
pa = pyaudio.PyAudio()

stream = pa.open(
    format=pyaudio.paInt16,
    channels=CHANNELS,
    rate=RATE,
    input=True,
    frames_per_buffer=CHUNK
)

print("🎤 Bắt đầu test mic... hãy vỗ tay")

while True:
    data = stream.read(CHUNK, exception_on_overflow=False)

    raw_audio = np.frombuffer(data, dtype=np.int16)

    audio_clip = audio_data.AudioData.create_from_array(
        raw_audio.astype(np.float32) / 32768.0,
        sample_rate=RATE
    )

    result = classifier.classify(audio_clip)

    for result in result:
        if result.classifications:
            for category in result.classifications[0].categories[:3]:
                print(category.category_name, f"{category.score:.2f}")

    print("-----")