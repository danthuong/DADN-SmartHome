# ⚙️ Installation & Setup

## 1️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate environment:

Linux / Mac:

```bash
source venv/bin/activate
```

Windows:

```bash
venv\Scripts\activate
```

## 2️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

## 3️⃣ Run AI Server

Open a terminal:

```bash
cd ai_server
uvicorn modules.face_recognition.backend.AI_backend:app --host 0.0.0.0 --port 8000
```

AI Server runs at: http://localhost:8000

## 4️⃣ Run Cam Backend

Open a new terminal:

```bash
cd ai_server
uvicorn modules.face_recognition.backend.CAM_backend:app --host 0.0.0.0 --port 9000
```

Cam Backend runs at: http://localhost:9000

## 5️⃣ Run Frontend

Open another terminal:

```bash
cd ai_server
python -m modules.face_recognition.backend.app
```

> **Demo Login Note:**  
> Since the project does **not yet support account registration**, please use the following credentials to log in:
>
> - **Username:** `account`
> - **Password:** `123456789`

> **CAM URL Configuration:**  
> In `ai_server/modules/face_recognition/backend/CAM_config.yaml`, update the default URL:
>
> ```yaml
> url: "http://192.168.137.208:8080/video"
> ```
>
> to point to your own camera stream URL.
