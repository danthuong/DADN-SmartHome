import cv2
import mediapipe as mp
import os
import csv
import numpy as np

# Khởi tạo MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, max_num_hands=1, min_detection_confidence=0.5)

def preprocess_landmarks(landmark_list):
    """Chuẩn hóa landmark: Dời gốc về cổ tay và scale theo kích thước tay"""
    temp_landmark_list = []
    # 1. Dời gốc tọa độ về điểm số 0 (Cổ tay)
    base_x, base_y = landmark_list[0][0], landmark_list[0][1]
    for x, y in landmark_list:
        temp_landmark_list.append([x - base_x, y - base_y])

    # 2. Chuẩn hóa khoảng cách (Scale)
    # Tính khoảng cách lớn nhất để đưa về đoạn [0, 1]
    max_value = max([max(abs(x), abs(y)) for x, y in temp_landmark_list])
    if max_value == 0: max_value = 1
    
    return [n / max_value for sublist in temp_landmark_list for n in sublist]

def run_extraction(data_dir, output_file):
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        # Header: 42 cột (21 điểm x 2 tọa độ x,y) + 1 cột nhãn
        header = [f"p{i}_{axis}" for i in range(21) for axis in ["x", "y"]] + ["label"]
        writer.writerow(header)

        # Duyệt qua các thư mục 1-one, 2-two...
        for category in sorted(os.listdir(data_dir)):
            cat_path = os.path.join(data_dir, category)
            if not os.path.isdir(cat_path) or "6-clap" in category:
                continue
            
            print(f"--- Đang xử lý nhãn: {category} ---")
            
            # Dùng os.walk để tìm hết ảnh trong mọi thư mục con (như two_up, two_up_inverted)
            for root, dirs, files in os.walk(cat_path):
                for filename in files:
                    if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                        img_path = os.path.join(root, filename)
                        image = cv2.imread(img_path)
                        if image is None: continue
                        
                        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                        results = hands.process(image_rgb)

                        if results.multi_hand_landmarks:
                            for hand_landmarks in results.multi_hand_landmarks:
                                landmark_list = [[lm.x, lm.y] for lm in hand_landmarks.landmark]
                                # Chuẩn hóa dữ liệu
                                processed_data = preprocess_landmarks(landmark_list)
                                # Ghi vào CSV
                                writer.writerow(processed_data + [category])

    print(f"Xong! Dữ liệu đã lưu vào {output_file}")

# Chạy lệnh (Thay 'data' bằng tên thư mục chứa các folder 1-one, 2-two...)
run_extraction('D:\DADN\DADN-SmartHome\\ai_server\modules\motion_detection\data', 'hand_gestures.csv')