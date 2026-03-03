# Đồ án đa ngành Smart Home tích hợp AI & IoT (Computer Vision)

Dự án xây dựng hệ thống nhà thông minh tích hợp trí tuệ nhân tạo (AI) chạy trên Edge Server để phân tích hình ảnh/video theo thời gian thực. Hệ thống kết hợp với mô hình phần cứng IoT (Yolo:Home) và ứng dụng di động để quản lý, điều khiển và tự động hóa các thiết bị trong nhà dựa trên nhận diện khuôn mặt, cử chỉ và sự hiện diện.

## Thành viên nhóm & Phân công
* **Phú Thịnh, Tuấn Duy:** Face Recognition (Nhận diện khuôn mặt, xác thực chủ nhà & cảnh báo an ninh).
* **Dương, Bảo Nhi:** Motion/Gesture Detection (Nhận diện cử chỉ tay để điều khiển đèn, quạt).
* **Yến Nhi, Phúc Thịnh:** Human Detection & Cảm biến (Tự động hóa môi trường rèm, đèn, quạt dựa trên hiện diện và cảm biến).

## Kiến trúc hệ thống
Hệ thống giao tiếp theo mô hình Pub/Sub thông qua **Adafruit IO** (MQTT Broker), bao gồm 3 thành phần chính:
1.  **AI Server (Python):** Chạy các model Deep Learning (YOLO, MediaPipe, FaceNet) để xử lý camera và ra quyết định.
2.  **Edge Device (Yolo:Bit/ESP32):** Điều khiển phần cứng vật lý (Relay, Servo, Đèn RGB) và thu thập dữ liệu cảm biến (Nhiệt độ, Ánh sáng).
3.  **Mobile App (Android):** Ứng dụng client cho phép người dùng cấu hình, đăng ký khuôn mặt và điều khiển thủ công (override).

---

## 📂 Cấu trúc thư mục (Repository Structure)

```text
SmartHome/
│
├── ai_server/                  # Mã nguồn chạy trên Edge AI Server (PC/Laptop)
│   ├── models/                 # Chứa các file trọng số AI (yolov11.pt, face_embeddings.dat)
│   ├── modules/                # Các module xử lý AI độc lập (để tránh conflict code)
│   │   ├── face_recognition/   # Module nhận diện chủ nhà / người lạ
│   │   ├── motion_detection/   # Module nhận diện cử chỉ tay 
│   │   └── human_detection/    # Module phát hiện hiện diện người
│   ├── database/               # Database
│   ├── mqtt_client.py          # Script kết nối pub/sub với Adafruit IO
│   ├── main.py                 # File chạy luồng chính (tích hợp Camera + AI + MQTT)
│   ├── requirements.txt        # Danh sách thư viện Python (opencv, mediapipe, ultralytics...)
│   └── .env                    # file biến môi trường 
│
├── edge_device/                # Mã nguồn nạp xuống vi điều khiển (Yolo:Bit/ESP32)
│   ├── lib/                    # Thư viện điều khiển phần cứng (NeoPixel, Servo, DHT)
│   ├── src/
│   │   └── main.py             # Logic điều khiển relay, đèn, quạt và đọc cảm biến
│   └── config.py.example       # File cấu hình mẫu chứa Wi-Fi SSID, Adafruit Key
│
├── mobile_app/                 # Mã nguồn ứng dụng điều khiển trên Android
│   ├── app/src/main/           # Giao diện UI/UX và logic Mobile
│   └── build.gradle            # File cấu hình build app
│
├── docs/                       # Tài liệu đồ án
│   ├── srs/                    # Đặc tả yêu cầu phần mềm (SRS - LaTeX)
│   ├── diagrams/               # Sơ đồ Use-case, Sequence, Architecture (Draw.io/UML)
│   └── reports/                # Báo cáo tiến độ, slide thuyết trình
│
├── .gitignore                  # Bỏ qua các file nhạy cảm (.env, venv, file weights lớn)
└── README.md                   # File tài liệu chính của dự án
