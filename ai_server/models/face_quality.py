from abc import ABC, abstractmethod
from PIL import Image
import numpy as np
import cv2

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


class FaceQualityModel(ABC):

    @abstractmethod
    def face_score(self, face_img: Image.Image, root_img: Image.Image) -> float:
        pass


class MediaPipe_Heuristic(FaceQualityModel):

    def __init__(self):

        base_options = python.BaseOptions(
            model_asset_path="./models/face_landmarker.task"
        )

        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            output_face_blendshapes=True,
            output_facial_transformation_matrixes=True,
            num_faces=1
        )

        self.detector = vision.FaceLandmarker.create_from_options(options)

    # -----------------------------
    # utils
    # -----------------------------
    def _pil_to_rgb(self, img: Image.Image):
        return np.array(img.convert("RGB"))

    def _compute_sharpness(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        return cv2.Laplacian(gray, cv2.CV_64F).var()

    def _landmark_center(self, landmarks, w, h):
        xs = [lm.x * w for lm in landmarks]
        ys = [lm.y * h for lm in landmarks]
        return np.mean(xs), np.mean(ys)

    def _face_bbox_ratio(self, landmarks, w, h):
        xs = [lm.x * w for lm in landmarks]
        ys = [lm.y * h for lm in landmarks]

        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        face_area = (x_max - x_min) * (y_max - y_min)
        img_area = w * h

        return face_area / img_area

    def _center_score(self, cx, cy, w, h):
        dx = abs(cx - w / 2) / (w / 2)
        dy = abs(cy - h / 2) / (h / 2)
        return 1.0 - min((dx + dy) / 2, 1.0)

    # -----------------------------
    # main score
    # -----------------------------
    def face_score(self, face_img: Image.Image, root_img: Image.Image) -> float:

        img = self._pil_to_rgb(root_img)
        h, w, _ = img.shape

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=img
        )

        result = self.detector.detect(mp_image)

        if not result.face_landmarks:
            return 0.0

        landmarks = result.face_landmarks[0]

        # 1. face size (scale lại cho đúng range)
        size_score = min(self._face_bbox_ratio(landmarks, w, h) * 10, 1.0)

        # 2. center
        cx, cy = self._landmark_center(landmarks, w, h)
        center_score = self._center_score(cx, cy, w, h)

        # 3. sharpness (ổn định hơn)
        sharpness = self._compute_sharpness(img)
        sharp_score = np.tanh(sharpness / 1000)

        # 4. pose quality (IMPORTANT FIX)
        if result.facial_transformation_matrixes:
            mat = result.facial_transformation_matrixes[0]

            # rough frontal estimation (z-axis tilt proxy)
            frontal_score = 1.0 - min(abs(mat[2][0]), 1.0)
        else:
            frontal_score = 0.5

        # -----------------------------
        # FINAL SCORE (realistic weights)
        # -----------------------------
        final_score = (
            0.45 * center_score +
            0.30 * frontal_score +
            0.15 * size_score +
            0.10 * sharp_score
        )

        return float(final_score)


if __name__ == "__main__":

    from PIL import Image

    model = MediaPipe_Heuristic()

    img = Image.open("test_1.jpg")

    score = model.face_score(img, img)

    print(f"Face quality score: {score:.4f}")