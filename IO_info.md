# TÀI LIỆU ĐẶC TẢ INPUT/OUTPUT (I/O) VÀ THIẾT KẾ SERVO
**Phân hệ:** Human Detection & IoT (Branch: `human_detection`)

## 1. Danh sách Input/Output (I/O) Thiết bị và Cảm biến

Bảng dưới đây liệt kê chi tiết luồng tín hiệu của các thiết bị phần cứng và AI được sử dụng trong hệ thống:

| Tên thiết bị / Cảm biến | Phân loại | Tín hiệu Nhận (Input) | Tín hiệu Trả (Output) | Giao thức / MQTT Feed |
| :--- | :--- | :--- | :--- | :--- |
| **Camera (YOLOv8)** | Input | Hình ảnh quang học (Video frames) | Tọa độ Bounding Box (x,y,w,h), Trạng thái 1/0 | Local / Python Variables |
| **Cảm biến PIR** | Input | Bức xạ hồng ngoại từ chuyển động | Tín hiệu Digital: 1 (Có người) / 0 (Không) | `human-detect-pir` |
| **Cảm biến Nhiệt độ** | Input | Nhiệt độ môi trường | Giá trị Float (VD: 32.5 độ C) | `env-temp` |
| **Cảm biến Ánh sáng** | Input | Cường độ ánh sáng | Giá trị Float/Int (VD: 150 lux) | `env-light` |
| **Quạt (Qua Relay)** | Output | Lệnh Digital: 1 (Bật) / 0 (Tắt) | Trạng thái quay cơ học (Tạo gió) | `device-fan` |
| **Đèn LED** | Output | Lệnh Digital: 1 (Bật) / 0 (Tắt) | Trạng thái phát sáng | `device-led` |
| **Động cơ Servo** | Output | Giá trị góc quay (0 đến 180 độ) | Chuyển động xoay bám sát mục tiêu | `device-servo` (Dự kiến) |

---

## 2. Thiết kế Lắp đặt Servo và Camera (Auto-Tracking)

### 2.1. Vị trí lắp đặt (Khoảng cách)
Để hệ thống có thể bám sát mục tiêu (người) một cách chính xác nhất mà không bị nhiễu do góc nhìn, giải pháp tối ưu là:
* **Khuyến nghị:** Bắt buộc lắp đặt Camera và Servo theo nguyên tắc **Đồng trục đứng (Coaxial)**.
* **Khoảng cách ngang (Trục X):** Tuyệt đối bằng 0 cm. Tâm của ống kính Camera phải nằm chính xác trên cùng một đường thẳng đứng với trục xoay của Servo.
* **Khoảng cách dọc (Trục Y):** Có thể linh hoạt (VD: cách nhau 5 - 10 cm), không ảnh hưởng đến thuật toán bám góc ngang.
* **Lý do:** Việc đặt đồng trục giúp loại bỏ hoàn toàn **sai số thị sai (Parallax Error)**. Do model YOLO 2D không đo lường được chiều sâu (Depth), nếu đặt lệch trục ngang, hệ thống sẽ không thể tính toán góc quay chuẩn xác cho các mục tiêu đứng ở khoảng cách xa gần khác nhau.

### 2.2. Công thức ánh xạ góc quay (Mapping Logic)
Để Servo tự động quay theo người dùng dựa trên tọa độ hộp sọ thu được từ YOLO, sử dụng thuật toán nội suy tuyến tính:

**Các tham số đầu vào:**
* `W`: Chiều rộng của khung hình Camera (VD: 640 pixels).
* `x`: Tọa độ tâm X của người dùng (0 <= x <= W) trích xuất từ tâm Bounding Box của YOLO.
* `FOV`: Góc nhìn ngang của Camera (Field of View, webcam thông thường là 60 độ).
* `Góc_Cân_Bằng`: Trạng thái Servo nhìn thẳng (Thường cài đặt ở 90 độ).

**Công thức tính toán:**
> Góc_Servo = Góc_Cân_Bằng + ((x - W/2) / W) * FOV

**Ví dụ thực tế:**
* Camera có độ phân giải ngang W = 640, góc nhìn FOV = 60 độ.
* YOLO phát hiện người đang di chuyển sang bên phải khung hình, tâm X đạt vị trí 480.
* Áp dụng công thức: `Góc_Servo = 90 + ((480 - 320) / 640) * 60 = 90 + 15 = 105 độ.`
* -> Kết luận: Hệ thống sẽ truyền lệnh góc `105` xuống YoloBit để Servo chĩa quạt/camera chính xác vào vị trí người đứng.