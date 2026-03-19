import numpy as np
import math

def preprocess_landmarks(kp_array_63):
    points = kp_array_63.reshape(21, 3)[:, :2]
    temp_list = []
    base_x, base_y = points[0][0], points[0][1]
    for x, y in points:
        temp_list.append([x - base_x, y - base_y])
    max_val = max([max(abs(x), abs(y)) for x, y in temp_list])
    if max_val == 0: max_val = 1
    return np.array(temp_list).flatten() / max_val

def calculate_tilt_angle(kp_array_63):
    points = kp_array_63.reshape(21, 3)
    p5 = points[5]   # Gốc ngón trỏ
    p17 = points[17] # Gốc ngón út
    angle = math.degrees(math.atan2(p17[1] - p5[1], p17[0] - p5[0]))
    return angle