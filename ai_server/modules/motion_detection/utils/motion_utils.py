import numpy as np
import torch


TARGET_FRAMES = 50 # Số frames cố định sau khi uniform sampling (25 frames cho 2 giây video)
MISSING_VALUE = -1.0

# Ánh xạ tên thư mục (hành động) thành số (Label)
LABEL_MAP = {
    "none": 0,
    "shake": 1,
    "clap": 2
}

LABELS = ["None", "Shake", "Clap"]

# ==========================================
# 1. FLIP DATA (DATA AUGMENTATION x2 dataset)
# ==========================================

def flip_sequence(raw_sequence):
    """
    Lật gương hành động: Đảo ngược trục X và hoán đổi vị trí Tay Trái <-> Tay Phải.
    Phải bảo vệ các giá trị -1.0 không bị biến thành 1.0.
    """
    flipped = np.copy(raw_sequence)
    
    # 1. Đảo ngược trục X 
    for i in range(0, 126, 3):
        # Chỉ đảo dấu nếu giá trị đó KHÁC -1.0
        valid_mask = flipped[:, i] != MISSING_VALUE
        flipped[valid_mask, i] = -flipped[valid_mask, i]
        
    # 2. Flip vị trí Tay Trái <-> Tay Phải (63 features mỗi tay)
    temp_left = np.copy(flipped[:, 0:63])
    flipped[:, 0:63] = flipped[:, 63:126]
    flipped[:, 63:126] = temp_left
    
    return flipped

# ==========================================
# 2. HÀM ÉP FRAME ĐỀU NHAU (Uniform Sampling)
# ==========================================
def resize_sequence_smoothly(sequence_data, target_frames=50, missing_val=-1.0):
    """
    Nội suy tuyến tính theo thời gian.
    Ví dụ: Biến mượt mà từ 40 frames lên 50 frames mà không bị lặp lại (khựng) frame.
    """
    total_frames = len(sequence_data)
    if total_frames == target_frames:
        return np.copy(sequence_data)
    if total_frames == 0:
        return np.full((target_frames, 126), missing_val)

    # Tạo trục thời gian giả lập (từ 0.0 đến 1.0)
    old_time = np.linspace(0, 2, total_frames)
    new_time = np.linspace(0, 2, target_frames)

    resized_seq = np.zeros((target_frames, 126))
    
    # Nội suy từng tọa độ (feature) một cách độc lập
    for i in range(126):
        # Nếu cột này toàn là tay tàng hình (-1.0), thì giữ nguyên -1.0
        if np.all(sequence_data[:, i] == missing_val):
            resized_seq[:, i] = missing_val
        else:
            # Nội suy tìm các điểm ảnh nằm giữa các frame
            resized_seq[:, i] = np.interp(new_time, old_time, sequence_data[:, i])
            
    return resized_seq


# ==========================================
# 3. HÀM TRÁM LỖ HỔNG (Forward & Backward Fill)
# ==========================================
def fill_missing_frames(sequence, missing_val=-1.0):
    """
    Điền các frame bị khuyết bằng phương pháp Nội suy Tuyến tính (Linear Interpolation).
    sequence: mảng numpy (50 frames, 126 tọa độ) sau khi đã uniform sampling. Các frame bị mất do nhiễu sẽ có giá trị -1.0 ở phần tay đó.
    """
    seq = np.copy(sequence)
    num_frames = len(seq)
    
    # Tạo một mảng chứa số thứ tự của tất cả các frame (Ví dụ: 0, 1, 2... 49)
    all_indices = np.arange(num_frames)
    
    # Xử lý độc lập Tay Trái (0 đến 62) và Tay Phải (63 đến 125)
    for hand_start in [0, 63]:
        hand_end = hand_start + 63
        
        # 1. Tìm index của các frame HỢP LỆ
        # Check phần tử đầu tiên của tay (seq[:, hand_start]) xem có khác -1.0 không
        valid_indices = np.where(seq[:, hand_start] != missing_val)[0]
        
        # Nếu tay này bị tàng hình 100% từ đầu đến cuối video -> Bỏ qua, giữ nguyên -1.0
        if len(valid_indices) == 0:
            continue
            
        # 2. Áp dụng nội suy cho TỪNG TỌA ĐỘ (63 features) của tay đó
        for feature_idx in range(hand_start, hand_end):
            # Bốc các giá trị hợp lệ của tọa độ trong tất cả các frame hợp lệ này ra
            valid_values = seq[valid_indices, feature_idx]
            
            # Hàm np.interp sẽ tự động điền trung bình vào giữa, kéo giãn ở 2 đầu
            seq[:, feature_idx] = np.interp(all_indices, valid_indices, valid_values)
            
    return seq

# ==========================================
# 4. HÀM CHUẨN HÓA TỌA ĐỘ (SEQUENCE-LEVEL)
# ==========================================
def normalize_sequence(sequence_data):
    seq = np.copy(sequence_data)
    pts = seq.reshape(-1, 3) # Gom thành danh sách các điểm 3D
    
    # Chỉ lấy những điểm KHÁC -1.0 để tính toán
    valid_mask = np.any(pts != MISSING_VALUE, axis=1)
    valid_pts = pts[valid_mask]

    if len(valid_pts) == 0:
        return seq

    # Dời tâm về trung bình cộng quỹ đạo
    global_center = np.mean(valid_pts, axis=0)
    pts[valid_mask] = valid_pts - global_center

    # Ép tỷ lệ 
    global_scale_factor = np.max(np.abs(pts[valid_mask]))
    if global_scale_factor > 0:
        pts[valid_mask] = pts[valid_mask] / global_scale_factor

    return pts.reshape(seq.shape)

# ==========================================
# 5. HÀM TÍNH VẬN TỐC
# ==========================================
def calculate_delta(sequence, missing_val=-1.0):
    """
    Tính Khung sau - Khung trước.
    Triệt tiêu vận tốc ảo khi tay đột ngột xuất hiện/biến mất.
    """
    delta = np.zeros_like(sequence)
    
    for i in range(1, len(sequence)):
        prev_frame = sequence[i-1]
        curr_frame = sequence[i]
        
        # Tạo mặt nạ: Chỉ tính delta ở những cột mà CẢ 2 FRAME ĐỀU CÓ TAY
        valid_mask = (prev_frame != missing_val) & (curr_frame != missing_val)
        
        # Chỉ trừ những phần hợp lệ. Những phần tay bị khuất sẽ tự động có vận tốc = 0.0
        delta[i][valid_mask] = curr_frame[valid_mask] - prev_frame[valid_mask]
        
    return delta

def full_pipeline(raw_sequence):
    """ 
    1. Trám lỗ hổng trên video gốc.
    2. Kéo giãn/Co rút thời gian mượt mà lên 50 frames.
    3. Chuẩn hóa không gian.
    4. Tính vận tốc.
    """
    # 1. Trám lỗ hổng trước
    filled = fill_missing_frames(raw_sequence)
    
    # 2. Nội suy thời gian 
    resized = resize_sequence_smoothly(filled, TARGET_FRAMES)
    
    # 3. Chuẩn hóa (Dùng hàm normalize_sequence từ tin nhắn trước của tôi)
    normed = normalize_sequence(resized)
    
    # 4. Tính Vận tốc
    delta = calculate_delta(normed)
    
    # cả tọa độ lẫn delta
    combined_features = np.concatenate((normed, delta), axis=1)
    
    return combined_features