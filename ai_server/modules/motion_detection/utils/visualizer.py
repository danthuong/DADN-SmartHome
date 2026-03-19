import cv2

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4), (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12), (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20)
]

def draw_hand_skeleton(frame, kp_array, w, h):
    points = kp_array.reshape(21, 3)
    pixel_points = []
    for p in points:
        cx, cy = int(p[0] * w), int(p[1] * h)
        pixel_points.append((cx, cy))
        cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1) 
    for connection in HAND_CONNECTIONS:
        pt1 = pixel_points[connection[0]]
        pt2 = pixel_points[connection[1]]
        cv2.line(frame, pt1, pt2, (255, 0, 0), 2)
    return pixel_points[0] # Trả về vị trí cổ tay để ghi chữ