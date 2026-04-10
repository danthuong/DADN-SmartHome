import os
import csv
import cv2
import numpy as np
import mediapipe as mp

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ===============================
# Initialize MediaPipe HandLandmarker
# ===============================

base_options = python.BaseOptions(
    model_asset_path="../../models/hand_landmarker.task"
)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    num_hands=1
)

detector = vision.HandLandmarker.create_from_options(options)


# ===============================
# Landmark normalization
# ===============================

def preprocess_landmarks(landmark_list):
    """
    Chuẩn hóa landmark:
    1. Dời gốc về cổ tay
    2. Scale theo kích thước bàn tay
    """

    temp_landmark_list = []

    base_x, base_y = landmark_list[0]

    for x, y in landmark_list:
        temp_landmark_list.append([x - base_x, y - base_y])

    max_value = max([max(abs(x), abs(y)) for x, y in temp_landmark_list])

    if max_value == 0:
        max_value = 1

    normalized = []

    for x, y in temp_landmark_list:
        normalized.append(x / max_value)
        normalized.append(y / max_value)

    return normalized


# ===============================
# Extract landmarks from image
# ===============================

def extract_landmarks(img_path):

    try:
        image = mp.Image.create_from_file(img_path)

        result = detector.detect(image)

        if not result.hand_landmarks:
            return None

        hand = result.hand_landmarks[0]

        landmark_list = []

        for lm in hand:
            landmark_list.append([lm.x, lm.y])

        return preprocess_landmarks(landmark_list)

    except:
        return None


# ===============================
# Dataset extraction
# ===============================

def run_extraction(data_dir, output_file):

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w", newline="") as f:

        writer = csv.writer(f)

        header = [f"p{i}_{axis}" for i in range(21) for axis in ["x", "y"]] + ["label"]
        writer.writerow(header)

        total_images = 0
        success = 0

        for category in sorted(os.listdir(data_dir)):

            cat_path = os.path.join(data_dir, category)

            if not os.path.isdir(cat_path):
                continue

            if category == "6-clap":
                continue

            print(f"\n--- Processing label: {category} ---")

            for root, dirs, files in os.walk(cat_path):

                for filename in files:

                    if not filename.lower().endswith((".png", ".jpg", ".jpeg")):
                        continue

                    img_path = os.path.join(root, filename)

                    total_images += 1

                    features = extract_landmarks(img_path)

                    if features is None:
                        continue

                    writer.writerow(features + [category])
                    success += 1

    print("\n==============================")
    print("Hoàn thành quá trình trích xuất")
    print("Tổng số ảnh:", total_images)
    print("Hoàn thành việc nhận diện:", success)
    print("Đã lưu vào:", output_file)
    print("==============================")


# ===============================
# Run script
# ===============================

if __name__ == "__main__":

    run_extraction(
        "../../data/raw",
        "../../data/processed/hand_gestures.csv"
    )