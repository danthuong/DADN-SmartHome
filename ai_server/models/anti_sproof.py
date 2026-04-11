from abc import ABC, abstractmethod
from PIL import Image
from typing import Literal

class AntiSproofModel(ABC):
    @abstractmethod
    def __init__(self, config):
        pass

    @abstractmethod
    def sproof_detect(
        self, 
        img: Image.Image
    ) -> Literal["real", "fake"]:
        pass

import os
import numpy as np
import cv2

from abc import ABC, abstractmethod
from PIL import Image
from typing import Literal

from modules.face_recognition.Silent_Face_Anti_Spoofing.src.anti_spoof_predict import AntiSpoofPredict
from modules.face_recognition.Silent_Face_Anti_Spoofing.src.generate_patches import CropImage
from modules.face_recognition.Silent_Face_Anti_Spoofing.src.utility import parse_model_name


class AntiSproofModel(ABC):

    @abstractmethod
    def __init__(self, config):
        pass

    @abstractmethod
    def sproof_detect(
        self,
        img: Image.Image
    ) -> Literal["real", "fake"]:
        pass


class SilentFaceModel(AntiSproofModel):

    def __init__(self, config):
        """
        config example:
        {
            "model_dir": "./resources/anti_spoof_models",
            "device_id": 0
        }
        """

        self.model_dir = config["model_dir"]
        self.device_id = config.get("device_id", 0)

        self.model_test = AntiSpoofPredict(self.device_id)
        self.image_cropper = CropImage()

    def _check_image(self, image):
        """
        Check ratio 4:3
        """

        height, width, channel = image.shape

        if width / height != 3 / 4:
            return False

        return True

    def _pil_to_cv2(self, img: Image.Image):

        img = np.array(img)

        if img.shape[-1] == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        return img

    def sproof_detect(
        self,
        img: Image.Image
    ) -> Literal["real", "fake"]:

        """
        Input:
            PIL Image

        Output:
            "real" or "fake"
        """

        # convert PIL -> OpenCV
        image = self._pil_to_cv2(img)

        # resize về 4:3 nếu cần
        height, width = image.shape[:2]

        if width / height != 3 / 4:
            image = cv2.resize(image, (480, 640))

        # get bbox
        image_bbox = self.model_test.get_bbox(image)

        prediction = np.zeros((1, 3))

        # loop qua models
        for model_name in os.listdir(self.model_dir):

            h_input, w_input, model_type, scale = parse_model_name(
                model_name
            )

            param = {
                "org_img": image,
                "bbox": image_bbox,
                "scale": scale,
                "out_w": w_input,
                "out_h": h_input,
                "crop": True,
            }

            if scale is None:
                param["crop"] = False

            img_crop = self.image_cropper.crop(**param)

            prediction += self.model_test.predict(
                img_crop,
                os.path.join(self.model_dir, model_name)
            )

        # get label
        label = np.argmax(prediction)

        if label == 1:
            return "real"
        else:
            return "fake"

import argparse
from PIL import Image
import os


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        type=str,
        required=True,
        help="path to image"
    )

    parser.add_argument(
        "--model_dir",
        type=str,
        default="modules/face_recognition/Silent_Face_Anti_Spoofing/resources/anti_spoof_models",
        help="model directory"
    )

    parser.add_argument(
        "--device_id",
        type=int,
        default=0
    )

    args = parser.parse_args()

    # check image exists
    if not os.path.exists(args.image):
        print("Image not found!")
        return

    # config
    config = {
        "model_dir": args.model_dir,
        "device_id": args.device_id
    }

    # load model
    print("Loading SilentFaceModel...")

    model = SilentFaceModel(config)

    # load image
    img = Image.open(args.image).convert("RGB")

    # predict
    result = model.sproof_detect(img)

    print("\n====================")
    print("Result:", result)
    print("====================\n")


if __name__ == "__main__":
    main()
