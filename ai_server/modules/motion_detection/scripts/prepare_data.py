import numpy as np
import os
import sys
import glob
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.motion_utils import *

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN & THÔNG SỐ
# ==========================================
DATASET_DIR = "D:/bku_docs/252/DADN/data" # Thư mục chứa các folder con: clap, shake, none...


# ==========================================
# 6. XỬ LÍ TOÀN BỘ DATASET
# ==========================================
def process_entire_dataset():
    print(f"\n[DATA_PREP] Bắt đầu quét dữ liệu tại: {DATASET_DIR}")
    
    X_data = []
    y_labels = []

    # Duyệt qua 3 thư mục: none, shake, clap
    for label_name, label_id in LABEL_MAP.items():
        folder_path = os.path.join(DATASET_DIR, label_name)
        
        if not os.path.exists(folder_path):
            print(f"[CẢNH BÁO] Không tìm thấy thư mục: {folder_path}")
            continue
            
        csv_files = glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True)
        print(f" -> Đang xử lý [{label_name.upper()}]: Tìm thấy {len(csv_files)} file CSV gốc.")
        
        count_processed = 0
        for file in csv_files:
            try:
                # Đọc data gốc
                raw_seq = np.loadtxt(file, delimiter=",")
                
                # 1. Đẩy data GỐC qua Pipeline
                processed_seq = full_pipeline(raw_seq)
                X_data.append(processed_seq)
                y_labels.append(label_id)
                
                # 2. Đẩy data LẬT GƯƠNG qua Pipeline (Nhân đôi Data)
                flipped_raw_seq = flip_sequence(raw_seq)
                processed_flipped_seq = full_pipeline(flipped_raw_seq)
                X_data.append(processed_flipped_seq)
                y_labels.append(label_id)
                
                count_processed += 2 # Tính cả gốc lẫn lật
                
            except Exception as e:
                print(f"Lỗi khi đọc file {file}: {e}")
                
        print(f"    => Đã tạo ra {count_processed} mẫu (Gốc + Lật gương) cho nhãn {label_name.upper()}.")

    # Đóng gói và lưu thành file numpy
    X_data = np.array(X_data, dtype=np.float32)
    y_labels = np.array(y_labels, dtype=np.int64)
    
    print("\n" + "="*50)
    print(f"✅ HOÀN THÀNH TẠO DATASET!")
    print(f"Tổng số mẫu huấn luyện (Total Samples): {len(X_data)}")
    print(f"Shape của X_data: {X_data.shape} (Samples, Frames, Features)")
    print(f"Shape của y_labels: {y_labels.shape}")
    print("="*50 + "\n")
    
    np.save("X_data.npy", X_data)
    np.save("y_labels.npy", y_labels)

if __name__ == "__main__":
    process_entire_dataset()