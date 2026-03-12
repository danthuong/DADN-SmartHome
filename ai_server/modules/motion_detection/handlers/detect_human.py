import os
import sys
sys.path.append(os.path.abspath("../"))
from human_detection.human_detector import HumanDetector

if __name__ == "__main__":
    detector = HumanDetector(model_path='yolov8x.pt', conf_threshold=0.6)

    print("[SYSTEM] Bắt đầu chạy Real-time. Bấm 'q' ở cửa sổ Camera để thoát.")

    while True:
        state = detector.scan_and_display()

        if state == 1:
            print("=> CẢNH BÁO: Phát hiện có người trong khung hình!")
        elif state == -1:
            print("=> LỖI: Mất tín hiệu Camera!")
            break

        if detector.check_exit():
            break

    detector.cleanup()