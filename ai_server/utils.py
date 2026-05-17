import math

def compute_servo_angle(
    cx,
    frame_width,
    focal_length_mm,
    sensor_width_mm,
    servo_center_angle=90
):
    """
    Tính góc quay servo giả định trục camera và trục servo trùng nhau (hoặc cách nhau không đáng kể).

    Tham số:
    - cx: Tọa độ x của tâm vật thể trong ảnh (pixel)
    - frame_width: Chiều rộng của khung hình (pixel)
    - focal_length_mm: Tiêu cự của camera (mm)
    - sensor_width_mm: Chiều rộng cảm biến camera (mm)
    - servo_center_angle: Góc trung tâm của servo (mặc định 90 độ)
    Trả về:
    - servo_angle: Góc quay servo cần thiết để hướng camera về phía vật thể
    """
    
    # 1. Tính focal length theo đơn vị pixel
    fx = (focal_length_mm * frame_width) / sensor_width_mm

    # 2. Khoảng cách từ tâm vật thể đến tâm ảnh (pixel)
    image_center_x = frame_width / 2
    dx = cx - image_center_x

    # 3. Tính góc camera nhìn vật (Radian)
    camera_angle_rad = math.atan(dx / fx)

    # 4. Đổi sang độ (Degree)
    # Vì giả định offset = 0 hoặc rất nhỏ, góc camera = góc servo
    angle_deg = math.degrees(camera_angle_rad)

    # 5. Cấp vào hệ tọa độ servo (Giả sử dx dương -> quay sang phải -> góc servo giảm)
    servo_angle = servo_center_angle - angle_deg

    # 6. Ép giới hạn an toàn vật lý
    return int(max(0, min(180, servo_angle)))