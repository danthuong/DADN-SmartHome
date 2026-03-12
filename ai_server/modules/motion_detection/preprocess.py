def preprocess_live_hand(landmark_list):
    """Chuẩn hóa dữ liệu từ Camera trước khi đưa vào Model"""
    temp_landmark_list = []
    # Dời gốc tọa độ về cổ tay (điểm 0)
    base_x, base_y = landmark_list[0][0], landmark_list[0][1]
    for x, y in landmark_list:
        temp_landmark_list.append([x - base_x, y - base_y])

    # Scale dữ liệu về đoạn [0, 1]
    max_value = max([max(abs(x), abs(y)) for x, y in temp_landmark_list])
    if max_value == 0: max_value = 1
    
    # Trả về mảng 1 chiều 42 phần tử
    return [n / max_value for sublist in temp_landmark_list for n in sublist]