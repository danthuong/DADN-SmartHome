import cv2
import os

def main():
    # =========================
    # 1️⃣ Nhập tên người
    # =========================
    name = input("Nhập tên người: ").strip()
    if name == "":
        print("Tên không hợp lệ!")
        return

    # =========================
    # 2️⃣ Tạo thư mục lưu ảnh
    # =========================
    save_dir = os.path.join("modules", "face_recognition", "baseImg", name)
    os.makedirs(save_dir, exist_ok=True)

    # Đếm số ảnh hiện có để tiếp tục đánh số
    existing_images = [
        f for f in os.listdir(save_dir) if f.startswith("img_") and f.endswith(".jpg")
    ]
    img_count = len(existing_images)

    # =========================
    # 3️⃣ Mở webcam
    # =========================
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Không mở được camera!")
        return

    print("Nhấn ENTER để chụp ảnh")
    print("Nhấn Q để thoát")

    # =========================
    # 4️⃣ Loop hiển thị camera
    # =========================
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Không đọc được frame!")
            break

        cv2.imshow("Camera", frame)

        key = cv2.waitKey(1) & 0xFF

        # Nhấn Enter để chụp (Enter = 13)
        if key == 13:
            img_path = os.path.join(save_dir, f"img_{img_count}.jpg")
            cv2.imwrite(img_path, frame)
            print(f"Đã lưu: {img_path}")
            img_count += 1

        # Nhấn Q để thoát
        elif key == ord('q'):
            print("Thoát chương trình.")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()