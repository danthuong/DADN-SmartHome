# Face Recognition System

## 📌 Overview

Hệ thống Face Recognition được thiết kế theo kiến trúc tách biệt thành 3 module chính:

- **AI Server** – xử lý Face Detection & Face Recognition
- **CAM Backend** – đại diện camera, xử lý streaming và tracking
- **Mobile App** – ứng dụng mobile để đăng ký và quản lý người dùng

Mục tiêu:

- Tách biệt AI khỏi camera
- Dễ scale AI Server
- Tối ưu realtime performance
- Dễ mở rộng thêm IoT / Authentication / Logging

---

# 🏗 System Architecture

```
Camera → CAM Backend → AI Server
                     ↘
                      Mobile App
```

---

# 🔹 Modules Description

## 1️⃣ AI Server

AI Server chịu trách nhiệm toàn bộ tác vụ AI:

- Face Detection
- Face Recognition (embedding + similarity)
- Face Cropping khi đăng ký
- Lưu embedding vào Database

### Processing Flow

1. Nhận frame từ CAM Backend hoặc ảnh từ Mobile App
2. Detect khuôn mặt
3. Trích xuất embedding
4. So sánh với database (cosine similarity)
5. Trả kết quả về cho CAM Backend hoặc Mobile App

> AI Server không xử lý tracking.

---

## 2️⃣ CAM Backend

CAM Backend đóng vai trò:

- Kết nối camera (USB/IP Camera)
- Capture frame realtime
- Gửi frame lên AI Server
- Nhận kết quả detection & recognition
- Gán instance tracking bằng DeepSORT
- Hiển thị kết quả lên màn hình

### Realtime Recognition Flow

1. Camera capture frame
2. Encode frame (base64)
3. Gửi HTTP request lên AI Server
4. Nhận kết quả:
   - Bounding boxes
   - Identity
   - Similarity score
5. Dùng DeepSORT:
   - Gán tracking ID
   - Theo dõi object qua nhiều frame
6. Render bounding box + name + track_id

> Tracking được xử lý tại CAM Backend để giảm tải AI Server.

---

## 3️⃣ Mobile App

Mobile App dùng để:

- Đăng ký chủ nhà
- Quản lý thông tin người dùng
- Nhận ảnh crop khuôn mặt
- Gửi thông tin xác nhận để lưu vào Database

---

# 🧑‍💻 Face Registration Flow

## 🔹 Cách 1: Upload từ Mobile

1. Mobile App gửi ảnh lên AI Server
2. AI Server:
   - Detect face
   - Crop face
   - Trả ảnh crop về Mobile App
3. Mobile App yêu cầu nhập thông tin (name, role, ...)
4. Mobile App gửi thông tin xác nhận về AI Server
5. AI Server:
   - Extract embedding
   - Lưu embedding + metadata vào Database

---

## 🔹 Cách 2: Chụp từ Camera

1. Mobile App yêu cầu CAM Backend chụp ảnh
2. CAM Backend capture frame
3. Gửi frame lên AI Server
4. AI Server detect & crop face
5. Trả ảnh crop về Mobile App
6. Người dùng nhập thông tin
7. Mobile App gửi xác nhận
8. AI Server lưu vào Database

---

# 🎥 Realtime Recognition Flow

```
Camera
   ↓
CAM Backend (capture frame)
   ↓
AI Server (detect + embedding + match)
   ↓
CAM Backend (DeepSORT tracking)
   ↓
Display result
```

Mỗi frame:

- AI Server trả về:
  - bbox
  - name (nếu match)
  - similarity score
- CAM Backend:
  - Gán track_id
  - Giữ ID ổn định qua nhiều frame
  - Render lên màn hình

---

# 🗄 Database Design (AI Server)

AI Server lưu:

- user_id
- name
- role
- embedding_vector
- created_at

Embedding có thể lưu:

- JSON
- Vector binary
- hoặc dạng phù hợp với DB đang dùng

---

# 🎯 Design Philosophy

- AI Server xử lý AI thuần
- CAM Backend xử lý realtime & tracking
- Mobile App xử lý UX
- Dễ scale AI Server độc lập
- Có thể deploy AI Server trên GPU server riêng

---

# 🚀 Future Improvements

- Logging hệ thống
- Authentication layer
- Multi-camera support
- IoT gateway integration
- Docker deployment
- Horizontal scaling AI Server

# 🚀 Getting Started

## 1️⃣ Clone Repository

```bash
git clone https://github.com/danthuong/DADN-SmartHome.git
```

---

# 🧠 Run AI Server

## 2️⃣ Move to AI Server Directory

```bash
cd ai_server
```

---

## 3️⃣ Create Virtual Environment

### 🔹 Windows

```bash
python -m venv venv
```

### 🔹 Linux / macOS

```bash
python3 -m venv venv
```

---

## 4️⃣ Activate Virtual Environment

### 🔹 Windows (PowerShell)

```bash
venv\Scripts\activate
```

### 🔹 Windows (CMD)

```bash
venv\Scripts\activate.bat
```

### 🔹 Linux / macOS

```bash
source venv/bin/activate
```

Sau khi activate thành công, bạn sẽ thấy `(venv)` ở đầu dòng terminal.

---

## 5️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

---

## 6️⃣ 📸 Upload Face Image (Register from Camera)

Để đăng ký khuôn mặt bằng camera local, chạy script test capture:

```bash
python -m test.test_cap_face
```

### 📌 Các bước thực hiện:

1. Nhập **tên người dùng** khi được yêu cầu.
2. Camera sẽ tự động bật lên.
3. Nhấn **Enter** để chụp ảnh.
4. Nhấn **q** để thoát chương trình.

---

### 📂 Image Storage

Sau khi chụp thành công, ảnh sẽ được lưu tại:

```
baseImg/<tên_người_dùng>/
```

Ví dụ:

```
baseImg/TuanDuy/
baseImg/PhuThinh/
```

Các ảnh này sẽ được sử dụng để:

- Gửi lên AI Server
- Extract embedding
- Lưu vào Database

---

💡 Lưu ý:

- Đảm bảo camera đang hoạt động trước khi chạy script.
- Nếu camera không mở được, kiểm tra lại device index trong OpenCV.

---

## 7️⃣ 🧠 Register Face to AI Server

Sau khi đã chụp và lưu ảnh vào thư mục `baseImg/`, tiến hành đăng ký khuôn mặt bằng cách chạy:

```bash
python -m modules.face_recognition.test.test_register_face
python -m modules.face_recognition.backend.app
```

---

### 📌 Quy trình hoạt động:

1. Hệ thống sẽ yêu cầu bạn **nhập tên folder**.
2. Model sẽ đọc toàn bộ ảnh trong thư mục:

```
<tên_folder>/
```

3. Với mỗi ảnh trong folder:
   - Detect tất cả khuôn mặt có trong ảnh.
   - Crop từng khuôn mặt riêng biệt.
4. Hiển thị từng khuôn mặt đã crop lên màn hình.
5. Với mỗi khuôn mặt, người dùng sẽ được yêu cầu nhập:
   - **Tên (name)**
   - **Location**
6. Sau khi nhập thông tin:
   - Model trích xuất embedding.
   - Lưu embedding + metadata vào Database.

---

### 🗄 Dữ liệu được lưu bao gồm:

- name
- location
- embedding_vector
- created_at

---

💡 Lưu ý:

- Nếu trong một ảnh có nhiều khuôn mặt, hệ thống sẽ yêu cầu nhập thông tin cho từng khuôn mặt.
- Chỉ cần nhập tên folder, không cần nhập full path.
- Sau khi đăng ký thành công, dữ liệu sẽ được dùng cho realtime recognition.

---

### ⚠️ Important Notes

- Hiện tại trong CAM Backend, location mặc định đang được set là:

```
house_A
```

👉 Vì vậy khi đăng ký khuôn mặt, bạn nên nhập:

```
location = house_A
```

để hệ thống nhận diện đúng khi chạy realtime.

- Model sẽ phân loại dựa trên **tên (name)**.
- Nếu bạn đăng ký nhiều ảnh của cùng một người trong cùng một location, hãy đảm bảo:
  - Điền **cùng một name**
  - Điền **cùng một location**

Ví dụ:

```
name: TuanDuy
location: house_A
```

Điều này giúp hệ thống:

- Gom embedding của cùng một người
- Tăng độ ổn định khi nhận diện realtime

---

```bash
cd ai_server
venv\Scripts\activate
uvicorn modules.face_recognition.backend.AI_backend:app --host 0.0.0.0 --port 8000
uvicorn modules.face_recognition.backend.CAM_backend:app --host 0.0.0.0 --port 9000
```

---

POST http://127.0.0.1:9000/register
{
"camera_url": "http://localhost:7000/video",
"location": "house_A"
}

# ✍️ Author

**Written by: nguyenphantuanduy**
