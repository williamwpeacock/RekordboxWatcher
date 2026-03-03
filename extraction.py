import pytesseract
import numpy as np
import cv2
from PIL import Image
from fuzzywuzzy import process

from pydantic import BaseModel
from typing import Tuple

# Extraction functions

def get_high_contrast_image(image):
    gry = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    (h, w) = gry.shape[:2]
    gry = cv2.resize(gry, (w * 2, h * 2))
    erd = cv2.erode(gry, None, iterations=1)
    thr = cv2.threshold(erd, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    # thr = cv2.threshold(erd, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    # bnt = cv2.bitwise_not(thr)
    return Image.fromarray(thr)

def closest_string(s, options):
    return process.extractOne(s, options)[0]

# Class definitions

class Coordinate(BaseModel):
    x: int
    y: int

    @staticmethod
    def from_json(json_obj):
        return Coordinate(x=json_obj[0], y=json_obj[1])

class BoundingBox(BaseModel):
    top_left: Coordinate
    bottom_right: Coordinate

    @staticmethod
    def from_json(json_obj):
        return BoundingBox(
            top_left=Coordinate.from_json(json_obj[0]),
            bottom_right=Coordinate.from_json(json_obj[1]),
        )

    def extract_from_image(self, image):
        return Image.fromarray(
            np.array(image)[int(min(self.top_left.y, self.bottom_right.y)) : int(max(self.top_left.y, self.bottom_right.y)),
                            int(min(self.top_left.x, self.bottom_right.x)) : int(max(self.top_left.x, self.bottom_right.x))],
                            "RGB")

class ExtractionArea(BaseModel):
    bb: BoundingBox

    @classmethod
    def from_json(cls, json_obj):
        return cls(
            bb=BoundingBox.from_json(json_obj)
        )

    def _extract_from_image(self, image) -> str | float | bool:
        return NotImplementedError("Extraction function not implemented")

    def extract_from_image(self, image) -> str | float | bool:
        sub_image = self.bb.extract_from_image(image)
        return self._extract_from_image(sub_image)

class TextExtraction(ExtractionArea):
    def _extract_from_image(self, image) -> str:
        new_image = get_high_contrast_image(image)
        text = pytesseract.image_to_string(new_image, lang='eng', config='--psm 7').strip()
        return text

class NumberExtraction(ExtractionArea):
    def _extract_from_image(self, image) -> float:
        new_image = get_high_contrast_image(image)
        num = pytesseract.image_to_string(new_image, config="--psm 7 digits").strip()
        return num

class ColorExtraction(ExtractionArea):
    def _extract_from_image(self, image) -> Tuple[int, int, int]:
        pix = np.array(image)
        color = np.mean(pix, axis=(0,1))
        return color

class ClosestTextExtraction(TextExtraction):
    def _extract_from_image(self, image, options) -> str:
        text = super()._extract_from_image(image)
        return closest_string(text, options)

# Specific implementations

class TimeExtraction(NumberExtraction):
    def _extract_from_image(self, image) -> float:
        text = super()._extract_from_image(image)
        # format: MM:SS.m
        text = text.replace(':', '')
        text = text.replace('.', '')
        if len(text) != 5:
            return -1

        return int(text[:2]) * 60 + int(text[2:4]) + int(text[4])/10

class BPMExtraction(NumberExtraction):
    def _extract_from_image(self, image) -> float:
        text = super()._extract_from_image(image)
        # format: (X)XX.XX
        text = text.replace('.', '')
        if len(text) < 3:
            return -1

        bpm_str = f"{text[:-2]}.{text[-2:]}"
        try:
            return float(bpm_str)
        except:
            return -1

class IsMasterExtraction(ColorExtraction):
    def _extract_from_image(self, image) -> bool:
        color = super()._extract_from_image(image)
        return color[0] > color[2]

class IsPlayingExtraction(ColorExtraction):
    def _extract_from_image(self, image) -> bool:
        color = super()._extract_from_image(image)
        return color[1] > color[2]

class ModeExtraction(ClosestTextExtraction):
    def _extract_from_image(self, image):
        return super()._extract_from_image(image, ["EXPORT", "PERFORMANCE", "LIGHTING", "EDIT"])

class LayoutExtraction(ClosestTextExtraction):
    def _extract_from_image(self, image):
        return super()._extract_from_image(image, ["2Deck Horizontal", "2Deck Vertical", "4Deck Horizontal", "4Deck Vertical", "Browse"])

class VolumeExtraction(ColorExtraction):
    def _extract_from_image(self, image) -> float:
        volume_vector = super()._extract_from_image(image)
        max_volume_vector = np.array([13.34736842, 75.51578947, 125.25263158])
        min_volume_vector = np.array([17.45789474, 17.45789474, 17.45789474])

        # red value throws calculation for some reason...
        value = np.mean((volume_vector[1:] - min_volume_vector[1:]) / (max_volume_vector[1:] - min_volume_vector[1:]))

        # ensure value is resonable
        return np.round(value, 2)

class EQExtraction(ColorExtraction):

    def extract_from_image(self, image) -> float:
        sub_image_1 = self.bb.extract_from_image(image)

        bb_2 = self.bb.model_copy()
        bb_2.top_left.x += 11
        bb_2.bottom_right.x += 11
        sub_image_2 = bb_2.extract_from_image(image)

        value = self._extract_from_image(sub_image_1)
        if value > 0:
            return (1-value) * 0.5
        else:
            return 0.5 + (self._extract_from_image(sub_image_2) * 0.5)

    def _extract_from_image(self, image) -> float:
        eq_vector = super()._extract_from_image(image)
        max_eq_vector = np.array([13.34736842, 75.51578947, 125.25263158])
        min_eq_vector = np.array([17.45789474, 17.45789474, 17.45789474])

        # print(eq_vector)
        return 1

        # red value throws calculation for some reason...
        value = np.mean((eq_vector - min_eq_vector) / (max_eq_vector - min_eq_vector))

        # ensure value is resonable
        return np.round(value, 2)
