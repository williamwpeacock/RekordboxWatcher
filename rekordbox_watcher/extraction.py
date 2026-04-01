import pytesseract
import numpy as np
import cv2
from PIL import Image
from fuzzywuzzy import process, utils
from sys import platform

from enum import Enum
from pydantic import BaseModel
from typing import Tuple, List, Dict, Optional

STRATEGY_MAP = {}

# Extraction functions

def get_high_contrast_image(image):
    """Converts image to grayscale, scales up, and uses erode and threshold to increase contrast.

    Args:
        image (?): Unprocessed image.

    Returns:
        Image: High contrast image.
    """
    gry = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
    (h, w) = gry.shape[:2]
    gry = cv2.resize(gry, (w * 2, h * 2))
    erd = cv2.erode(gry, None, iterations=1)
    thr = cv2.threshold(erd, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    return Image.fromarray(thr)

def closest_string(s, options):
    """Finds closest match to string from list of options, empty string if string can't be processed.

    Args:
        s (str): Origin string.
        options (list of str): Target strings.

    Returns:
        str: Closest match, or empty string.
    """
    if utils.full_process(s):
        return process.extractOne(s, options)[0]
    else:
        return ""

# Class definitions

class Coordinate(BaseModel):
    """Position of pixel in image.

    Attributes:
        x (int): X value in pixels.
        y (int): Y value in pixels.
    """
    x: int
    y: int

    @staticmethod
    def from_json(json_obj):
        return Coordinate(x=json_obj[0], y=json_obj[1])

class BoundingBox(BaseModel):
    """Box containing key feature in image.

    Attributes:
        top_left (Coordinate): Position of top left pixel.
        bottom_right (Coordinate): Position of bottom right pixel.
    """
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
                            int(min(self.top_left.x, self.bottom_right.x)) : int(max(self.top_left.x, self.bottom_right.x))]) #,
                            # "RGB")

class ExtractionArea(BaseModel):
    """Base class for extraction strategy.

    Attributes:
        bb (BoundingBox): Location of feature.
    """
    bb: BoundingBox

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        STRATEGY_MAP[cls.__name__] = cls

    @classmethod
    def from_json(cls, json_obj):
        return cls(
            bb=BoundingBox.from_json(json_obj)
        )

    def _extract_from_image(self, image) -> str | float | bool:
        raise NotImplementedError("Extraction function not implemented")

    def extract_from_image(self, image) -> str | float | bool:
        sub_image = self.bb.extract_from_image(image)
        return self._extract_from_image(sub_image)

class TextExtraction(ExtractionArea):
    """Strategy to extract text from image."""
    def _extract_from_image(self, image) -> str:
        new_image = get_high_contrast_image(image)
        text = pytesseract.image_to_string(new_image, lang='eng', config='--psm 7').strip()
        return text

class NumberExtraction(ExtractionArea):
    """Strategy to extract number from image."""
    def _extract_from_image(self, image) -> float:
        new_image = get_high_contrast_image(image)
        num = pytesseract.image_to_string(new_image, config="--psm 7 digits").strip()
        return num

class ColorExtraction(ExtractionArea):
    """Strategy to extract color from image."""
    def _extract_from_image(self, image) -> Tuple[int, int, int]:
        pix = np.array(image)
        color = np.mean(pix, axis=(0,1))
        return color

class ClosestTextExtraction(TextExtraction):
    """Strategy to extract text from image given a list of possible values."""
    def _extract_from_image(self, image, options) -> str:
        text = super()._extract_from_image(image)
        return closest_string(text, options)

# Specific implementations

class IsLoadedExtraction(ColorExtraction):
    """Strategy to extract is_loaded boolean from image."""
    def _extract_from_image(self, image) -> bool:
        color = super()._extract_from_image(image)
        return not (color[0] > color[2])

class TimeExtraction(NumberExtraction):
    """Strategy to extract time value from image."""
    def _extract_from_image(self, image) -> float:
        text = super()._extract_from_image(image)
        # format: MM:SS.m
        text = text.replace(':', '')
        text = text.replace('.', '')
        if len(text) != 5:
            return -1

        try:
            return int(text[:2]) * 60 + int(text[2:4]) + int(text[4])/10
        except ValueError:
            return -1

class BPMExtraction(NumberExtraction):
    """Strategy to extract BPM value from image."""
    def _extract_from_image(self, image) -> float:
        text = super()._extract_from_image(image)
        # format: (X)XX.XX
        text = text.replace('.', '')
        if len(text) < 3:
            return -1

        bpm_str = f"{text[:-2]}.{text[-2:]}"
        try:
            return float(bpm_str)
        except ValueError:
            return -1

class IsMasterExtraction(ColorExtraction):
    """Strategy to extract is_master boolean from image."""
    def _extract_from_image(self, image) -> bool:
        color = super()._extract_from_image(image)
        return color[0] > color[2]

class IsPlayingExtraction(ColorExtraction):
    """Strategy to extract is_playing boolean from image."""
    def _extract_from_image(self, image) -> bool:
        color = super()._extract_from_image(image)
        return color[1] > color[2]

class ModeExtraction(ClosestTextExtraction):
    """Strategy to extract mode from image."""
    def _extract_from_image(self, image):
        image.show()
        return super()._extract_from_image(image, ["EXPORT", "PERFORMANCE", "LIGHTING", "EDIT"])

class LayoutExtraction(ClosestTextExtraction):
    """Strategy to extract layout from image."""
    def _extract_from_image(self, image):
        return super()._extract_from_image(image, ["2Deck Horizontal", "2Deck Vertical", "4Deck Horizontal", "4Deck Vertical", "Browse"])

class VolumeExtraction(ColorExtraction):
    """Strategy to extract volume value from image."""
    def _extract_from_image(self, image) -> float:
        volume_vector = super()._extract_from_image(image)
        max_volume_vector = np.array([0.38947368, 124.72631579, 224.2])
        min_volume_vector = np.array([5.28421053, 5.28421053, 5.28421053])

        # red value throws calculation for some reason...
        value = np.mean((volume_vector[1:] - min_volume_vector[1:]) / (max_volume_vector[1:] - min_volume_vector[1:]))

        # ensure value is resonable
        return np.round(value, 2)

class EQExtraction(ColorExtraction):
    """Strategy to extract EQ value from image."""
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

# Scaling

class ScaledAnchorPoints(BaseModel):
    deck_left_pos: int
    deck_right_pos: int
    mixer_left_pos: int
    mixer_right_pos: int
    y_offset: int

    def _anchor_to(self, left_pos, right_pos, property_config):
        result = [[0, 0], [0, 0]]

        left_x = property_config.bb[0][0]
        if property_config.left_anchor == "LEFT":
            result[0][0] = left_pos + left_x
        elif property_config.left_anchor == "RIGHT":
            result[0][0] = right_pos + left_x

        result[0][1] = (property_config.bb[0][1] + self.y_offset)

        right_x = property_config.bb[1][0]
        if property_config.right_anchor == "LEFT":
            result[1][0] = left_pos + right_x
        elif property_config.right_anchor == "RIGHT":
            result[1][0] = right_pos + right_x

        result[1][1] = (property_config.bb[1][1] + self.y_offset)

        return result

    def anchor_to_deck(self, property_config):
        return self._anchor_to(self.deck_left_pos, self.deck_right_pos, property_config)

    def anchor_to_mixer(self, property_config):
        return self._anchor_to(self.mixer_left_pos, self.mixer_right_pos, property_config)

class Platform(str, Enum):
    WINDOWS = "windows"
    MAC = "mac"
    UNKNOWN = "unknown"

    @staticmethod
    def detect(self):
        if platform in ["win32", "win64"]:
            return Platform.WINDOWS
        elif platform == "darwin":
            return Platform.MAC
        else:
            return Platform.UNKNOWN

class Scaler(BaseModel):
    screen_width: int
    screen_height: int
    mixer_width: int
    y_offset: int

    @property
    def default_deck_width(self):
        return (self.screen_width - self.mixer_width) / 2

    @staticmethod
    def get_y_offset(platform):
        if platform == Platform.WINDOWS:
            return 0
        elif platform == Platform.MAC:
            return -45
        else:
            raise ValueError(f"Unkown Y offset for platform: {platform}")

    def calculate_scaling_factor(self, current_screen_width):
        return (current_screen_width - self.mixer_width) / (self.screen_width - self.mixer_width)

    def calculate_current_deck_width(self, current_screen_width):
        scaling_factor = self.calculate_scaling_factor(current_screen_width)
        return scaling_factor * self.default_deck_width

    def get_mixer_x_pos(self, current_screen_width):
        return self.calculate_current_deck_width(current_screen_width)

    def get_deck_x_pos(self, deck_num, current_screen_width):
        is_left_deck = (deck_num % 2 == 0)
        if is_left_deck:
            return 0

        return self.calculate_current_deck_width(current_screen_width) + self.mixer_width

    def get_scaled_anchor_points(self, deck_num, current_screen_width):
        deck_left_pos = self.get_deck_x_pos(deck_num, current_screen_width)
        deck_right_pos = deck_left_pos + self.calculate_current_deck_width(current_screen_width)
        mixer_left_pos = self.get_mixer_x_pos(current_screen_width)
        mixer_right_pos = mixer_left_pos + self.mixer_width

        return ScaledAnchorPoints(
            deck_left_pos = int(deck_left_pos),
            deck_right_pos = int(deck_right_pos),
            mixer_left_pos = int(mixer_left_pos),
            mixer_right_pos = int(mixer_right_pos),
            y_offset = self.y_offset
        )

# Extraction strategy factory and containers

class DeckExtractionStrategies(BaseModel):
    song: Optional[TextExtraction] = None
    is_loaded: Optional[IsLoadedExtraction] = None
    artist: Optional[TextExtraction] = None
    is_master: Optional[IsMasterExtraction] = None
    bpm: Optional[BPMExtraction] = None
    time: Optional[TimeExtraction] = None
    is_playing: Optional[IsPlayingExtraction] = None
    volume: Optional[VolumeExtraction] = None
    high: Optional[EQExtraction] = None
    medium: Optional[EQExtraction] = None
    low: Optional[EQExtraction] = None

    def __init__(self, anchor_points: ScaledAnchorPoints, deck_config):
        super().__init__()
        deck_properties_dict = deck_config.deck_properties.__dict__
        for property_name, property_config in deck_properties_dict.items():
            extraction_cls = property_config.extraction_strategy
            anchored_bb = anchor_points.anchor_to_deck(property_config)
            obj = extraction_cls(
                bb=BoundingBox.from_json(anchored_bb)
            )
            setattr(self, property_name, obj)

        mixer_properties_dict = deck_config.mixer_properties.__dict__
        for property_name, property_config in mixer_properties_dict.items():
            extraction_cls = property_config.extraction_strategy
            anchored_bb = anchor_points.anchor_to_mixer(property_config)
            obj = extraction_cls(
                bb=BoundingBox.from_json(anchored_bb)
            )
            setattr(self, property_name, obj)

class ExtractionStrategies(BaseModel):
    decks: List[DeckExtractionStrategies]

    def __init__(self, scaler: "Scaler", screen_width: int, deck_configs):
        super().__init__(decks=[])

        for deck_num, deck_config in enumerate(deck_configs):
            anchor_points = scaler.get_scaled_anchor_points(deck_num, screen_width)
            self.decks.append(
                DeckExtractionStrategies(
                    anchor_points = anchor_points,
                    deck_config = deck_config
                )
            )

class ExtractionStrategyFactory(BaseModel):
    scaler: Scaler
    _extraction_strategies: Dict[int, Dict[str, ExtractionStrategies]]

    def get_strategies(self, width, layout_config) -> ExtractionStrategies:
        if not hasattr(self, "_extraction_strategies"):
            self._extraction_strategies = {}

        if width not in self._extraction_strategies:
            self._extraction_strategies[width] = {}

        layout_str = layout_config.name

        if layout_str not in self._extraction_strategies[width]:
            self._extraction_strategies[width][layout_str] = ExtractionStrategies(self.scaler, width, layout_config.deck_configs)

        return self._extraction_strategies[width][layout_str]
