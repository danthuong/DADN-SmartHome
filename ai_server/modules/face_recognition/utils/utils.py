import cv2
from database.FRDb import Info

def detect_face(model, img):
    return model.detect(img)


def crop_face(img, faces):
    results = []

    h, w = img.shape[:2]

    for face in faces:
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox

        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        face_img = img[y1:y2, x1:x2]

        if face_img.size == 0:
            continue

        results.append((face_img, face))

    return results

def add_face(db, face_list):
    ids = []

    for face_img, face, info in face_list:
        image_id = db.updateEmbedding(
            info=info,
            embedding=face.embedding,
            img=face_img,
        )
        ids.append(image_id)

    return ids

def iou(boxA, boxB):
    # box = [x1, y1, x2, y2]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    if boxAArea + boxBArea - interArea == 0:
        return 0

    return interArea / float(boxAArea + boxBArea - interArea)