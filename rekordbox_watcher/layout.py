import json

from pydantic import BaseModel
from enum import Enum
from typing import List, Optional, Dict, Type

from .extraction import ExtractionStrategyFactory, ExtractionStrategies, ModeExtraction, LayoutExtraction, ExtractionArea, STRATEGY_MAP, Scaler

def load_from_json(json_path):
    """Imports bounding boxes from JSON."""
    with open(json_path, "r") as f:
        json_obj = json.loads(f.read())

    return Config.from_json(json_obj)

class AnchorSide(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"

class Property(BaseModel):
    bb: List[List[int]]
    left_anchor: AnchorSide
    right_anchor: AnchorSide
    extraction_strategy: Type[ExtractionArea]

    @staticmethod
    def from_json(json_obj):
        extraction_strategy = STRATEGY_MAP[json_obj["extraction_strategy"]]
        return Property(
            bb = json_obj["bb"],
            left_anchor = json_obj["left_anchor"],
            right_anchor = json_obj["right_anchor"],
            extraction_strategy = extraction_strategy,
        )

class DeckProperties(BaseModel):
    song: Property
    is_loaded: Property

    artist: Property

    is_master: Property
    time: Property

    bpm: Property
    is_playing: Property

    @staticmethod
    def from_json(json_obj):
        return DeckProperties(
            song = Property.from_json(json_obj["song"]),
            is_loaded = Property.from_json(json_obj["is_loaded"]),
            artist = Property.from_json(json_obj["artist"]),
            is_master = Property.from_json(json_obj["is_master"]),
            time = Property.from_json(json_obj["time"]),
            bpm = Property.from_json(json_obj["bpm"]),
            is_playing = Property.from_json(json_obj["is_playing"])
        )

class MixerProperties(BaseModel):
    volume: Property
    high: Property
    medium: Property
    low: Property

    @staticmethod
    def from_json(json_obj):
        return MixerProperties(
            volume = Property.from_json(json_obj["volume"]),
            high = Property.from_json(json_obj["high"]),
            medium = Property.from_json(json_obj["medium"]),
            low = Property.from_json(json_obj["low"])
        )

class DeckConfig(BaseModel):
    deck_properties: DeckProperties
    mixer_properties: MixerProperties

    @staticmethod
    def from_json(json_obj):
        return DeckConfig(
            deck_properties = DeckProperties.from_json(json_obj["deck_properties"]),
            mixer_properties = MixerProperties.from_json(json_obj["mixer_properties"]),
        )

class LayoutConfig(BaseModel):
    name: str
    deck_configs: List[DeckConfig]

    @staticmethod
    def from_json(name, json_obj):
        return LayoutConfig(
            name = name,
            deck_configs = [DeckConfig.from_json(deck) for deck in json_obj]
        )

class Config(BaseModel):
    """Extraction strategies for a rekordbox session.

    Attributes:
        mode (ModeExtraction): Extraction strategy for mode string.
        layout (LayoutExtraction): Extraction strategy for layout string.
        layout_configs (list of LayoutConfig): Extraction strategies for each layout.
    """
    extraction_strategy_factory: ExtractionStrategyFactory
    mode: ModeExtraction
    layout: LayoutExtraction
    layout_configs: Dict[str, LayoutConfig]

    @staticmethod
    def from_json(json_obj):
        scaler = Scaler(
            screen_width = json_obj["screen_width"],
            screen_height = json_obj["screen_height"],
            mixer_width = json_obj["mixer_width"]
        )
        return Config(
            extraction_strategy_factory = ExtractionStrategyFactory(
                scaler = scaler
            ),
            mode=ModeExtraction.from_json(json_obj["mode"]),
            layout=LayoutExtraction.from_json(json_obj["layout"]),
            layout_configs={
                name: LayoutConfig.from_json(name, deck_layouts) for name, deck_layouts in json_obj["layout_configs"].items()
            }
        )

    def get_extraction_strategies(self, image) -> Optional[ExtractionStrategies]:
        """Extracts mode and layout and returns matching ExtractionStrategies object, or None."""
        mode_str = self.mode.extract_from_image(image)
        if mode_str != "PERFORMANCE":
            return None

        layout_str = self.layout.extract_from_image(image)
        if layout_str in self.layout_configs:
            width, _ = image.size
            return self.extraction_strategy_factory.get_strategies(width, self.layout_configs[layout_str])

        return None
