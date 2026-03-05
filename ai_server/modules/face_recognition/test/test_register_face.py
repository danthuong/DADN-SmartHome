import os
import cv2
from models.model import FRModel
from database.FRDb import FRDb, Info, DbFactory
from ..utils.utils import detect_face, crop_face, add_face 
from models.model import ModelFactory
from modules.face_recognition.config.config import Retina_ArcConfig, JSONDbConfig

def choose_faces_and_input_info(cropped_faces):
    face_list = []

    for i, (face_img, face) in enumerate(cropped_faces):
        print(f"\nFace {i}")
        cv2.imshow(f"Face {i}", face_img)
        cv2.waitKey(1)

        name = input("Enter name (or 'skip'): ").strip()
        if name.lower() == "skip":
            cv2.destroyWindow(f"Face {i}")
            continue

        location = input("Enter location (optional): ").strip()

        info = Info(
            name=name if name else None,
            location=location if location else None,
        )

        face_list.append((face_img, face, info))

        cv2.destroyWindow(f"Face {i}")

    cv2.destroyAllWindows()
    return face_list


def main():
    # =========================
    # 1️⃣ Init DB
    # =========================
    dbConfig = JSONDbConfig(
        "frdb.json",
        "images"
    )
    db = DbFactory.create("jsonDb", dbConfig)

    # =========================
    # 2️⃣ Nhập folder ảnh
    # =========================
    # Nhập name và location
    name = input("Enter name: ").strip()

    # Lấy root project
    # Tạo đường dẫn tự động
    img_folder = os.path.join(
        "modules",
        "face_recognition",
        "baseImg",
        name
    )

    if not os.path.isdir(img_folder):
        print("Folder not found:", img_folder)
        return

    # =========================
    # 3️⃣ Init Model (chỉ load 1 lần)
    # =========================
    modelConfig = Retina_ArcConfig(
        device="cpu",
        det_size=640,
        scale="l"
    )

    model = ModelFactory.create("retina_arc", modelConfig)

    # =========================
    # 4️⃣ Duyệt toàn bộ ảnh trong folder
    # =========================
    all_files = os.listdir(img_folder)
    image_files = [
        f for f in all_files
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if len(image_files) == 0:
        print("No images found in folder.")
        return

    for file_name in image_files:
        img_path = os.path.join(img_folder, file_name)
        print(f"\nProcessing: {file_name}")

        img = cv2.imread(img_path)
        if img is None:
            print("Cannot read image.")
            continue

        faces = detect_face(model, img)

        if len(faces) == 0:
            print("No faces detected.")
            continue

        cropped_faces = crop_face(img, faces)

        if len(cropped_faces) == 0:
            print("No valid faces.")
            continue

        face_list = choose_faces_and_input_info(cropped_faces)

        if len(face_list) == 0:
            print("No face selected.")
            continue

        ids = add_face(db, face_list)
        print("Saved IDs:", ids)

    print("\nDone processing all images.")


if __name__ == "__main__":
    main()