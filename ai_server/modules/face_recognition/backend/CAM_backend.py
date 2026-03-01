import cv2
import requests
import base64
import numpy as np
import argparse
from deep_sort_realtime.deepsort_tracker import DeepSort

AI_URL = "http://127.0.0.1:8000/detect"


def encode_frame(frame):
    _, buffer = cv2.imencode(".jpg", frame)
    return base64.b64encode(buffer).decode("utf-8")


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


def main(location):
    cap = cv2.VideoCapture(0)

    tracker = DeepSort(
        max_age=8,
        n_init=3,  
        max_cosine_distance=0.4,
        embedder=None
    )

    if not cap.isOpened():
        print("Cannot open camera")
        return

    print(f"Starting camera with location = {location}")

    id_name_map = {}

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.resize(frame, (640, 480))
        img_base64 = encode_frame(frame)

        try:
            response = requests.post(
                AI_URL,
                json={
                    "frame": img_base64,
                    "location": location
                },
                timeout=5
            )
            detections = response.json()
        except Exception as e:
            print("AI error:", e)
            detections = []

        # =============================
        # Chuẩn bị dữ liệu cho DeepSort
        # =============================

        ds_inputs = []
        embeddings = []
        det_boxes = []
        det_names = []

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            embedding = np.array(det["embedding"], dtype=np.float32)
            name = det["name"]

            w = x2 - x1
            h = y2 - y1

            ds_inputs.append(([x1, y1, w, h], 1.0, "face"))
            embeddings.append(embedding)
            det_boxes.append([x1, y1, x2, y2])
            det_names.append(name)

        # =============================
        # Update tracker
        # =============================

        tracks = tracker.update_tracks(ds_inputs, embeds=embeddings)

        # =============================
        # Gán name dựa trên IoU match
        # =============================

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = track.track_id
            l, t, r, b = track.to_ltrb()
            track_box = [int(l), int(t), int(r), int(b)]

            best_iou = 0
            matched_name = "Unknown"

            # tìm detection trùng box nhiều nhất
            for det_box, det_name in zip(det_boxes, det_names):
                score = iou(track_box, det_box)
                if score > best_iou:
                    best_iou = score
                    matched_name = det_name

            # nếu track chưa có tên
            if track_id not in id_name_map:
                if matched_name != "Unknown":
                    id_name_map[track_id] = matched_name
                else:
                    id_name_map[track_id] = "Unknown"

            # nếu trước đó là Unknown nhưng giờ detect được tên
            elif id_name_map[track_id] == "Unknown" and matched_name != "Unknown":
                id_name_map[track_id] = matched_name

            name = id_name_map[track_id]

            # =============================
            # Draw
            # =============================

            cv2.rectangle(
                frame,
                (track_box[0], track_box[1]),
                (track_box[2], track_box[3]),
                (0, 255, 0),
                2
            )

            cv2.putText(
                frame,
                f"{name} | ID {track_id}",
                (track_box[0], track_box[1] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )

        cv2.imshow(f"CAM - {location}", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--location",
        type=str,
        required=True,
        help="Camera location / house ID"
    )
    args = parser.parse_args()

    main(args.location)