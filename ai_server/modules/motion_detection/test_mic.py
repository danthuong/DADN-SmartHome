import pyaudio
import numpy as np

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

p = pyaudio.PyAudio()

stream = p.open(
format=FORMAT,
channels=CHANNELS,
rate=RATE,
input=True,
frames_per_buffer=CHUNK
)

print("Đang nghe microphone... (Ctrl+C để dừng)")

try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        audio = np.frombuffer(data, dtype=np.int16)

        volume = np.linalg.norm(audio) / len(audio)
        print("Volume:", volume)

except KeyboardInterrupt:
    print("Dừng test mic")

stream.stop_stream()
stream.close()
p.terminate()
