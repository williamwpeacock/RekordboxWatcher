import json

from pydantic import BaseModel
from typing import List, Optional

from .extraction import TextExtraction, BPMExtraction, TimeExtraction, IsMasterExtraction, IsPlayingExtraction, ModeExtraction, LayoutExtraction, VolumeExtraction, EQExtraction, IsLoadedExtraction

def load_from_json(json_path):
    """Imports bounding boxes from JSON."""
    with open(json_path, "r") as f:
        json_obj = json.loads(f.read())

    return Config.from_json(json_obj)

class EQConfig(BaseModel):
    """Extraction strategies for EQ values.

    Attributes:
        high (EQExtraction): Extraction strategy for high EQ value.
        medium (EQExtraction): Extraction strategy for medium EQ value.
        low (EQExtraction): Extraction strategy for low EQ value.
    """
    high: EQExtraction
    medium: EQExtraction
    low: EQExtraction

    @staticmethod
    def from_json(json_obj):
        return EQConfig(
            high=EQExtraction.from_json(json_obj["high"]),
            medium=EQExtraction.from_json(json_obj["medium"]),
            low=EQExtraction.from_json(json_obj["low"])
        )

class DeckConfig(BaseModel):
    """Extraction strategies for a deck.

    Attributes:
        song (TextExtraction): Extraction strategy for song name.
        is_loaded (IsLoadedExtraction): Extraction strategy for is_loaded boolean.
        artist (TextExtraction): Extraction strategy for artist name.
        is_master (IsMasterExtraction): Extraction strategy for is_master boolean.
        bpm (BPMExtraction): Extraction strategy for BPM value.
        time (TimeExtraction): Extraction strategy for time value.
        is_playing (IsPlayingExtraction): Extraction strategy for is_playing boolean.
        volume (VolumeExtraction): Extraction strategy for volume value.
        eq (EQConfig): Extraction strategies for EQ values.
    """
    song: TextExtraction
    is_loaded: IsLoadedExtraction
    artist: TextExtraction
    is_master: IsMasterExtraction
    bpm: BPMExtraction
    time: TimeExtraction
    is_playing: IsPlayingExtraction
    volume: VolumeExtraction
    eq: EQConfig

    @staticmethod
    def from_json(json_obj):
        return DeckConfig(
            song=TextExtraction.from_json(json_obj["song"]),
            is_loaded=IsLoadedExtraction.from_json(json_obj["song"]),
            artist=TextExtraction.from_json(json_obj["artist"]),
            is_master=IsMasterExtraction.from_json(json_obj["is_master"]),
            bpm=BPMExtraction.from_json(json_obj["bpm"]),
            time=TimeExtraction.from_json(json_obj["time"]),
            is_playing=IsPlayingExtraction.from_json(json_obj["is_playing"]),
            volume=VolumeExtraction.from_json(json_obj["volume"]),
            eq=EQConfig.from_json(json_obj["eq"])
        )

class LayoutConfig(BaseModel):
    """Extraction strategies for a layout.

    Attributes:
        name (str): Layout name.
        decks (list of DeckConfig): Extraction strategies for each deck.
    """
    name: str
    decks: List[DeckConfig]

    @staticmethod
    def from_json(json_obj):
        name, deck_layouts = list(json_obj.items())[0]
        return LayoutConfig(name=name, decks=[DeckConfig.from_json(deck) for deck in deck_layouts])

class Config(BaseModel):
    """Extraction strategies for a rekordbox session.

    Attributes:
        mode (ModeExtraction): Extraction strategy for mode string.
        layout (LayoutExtraction): Extraction strategy for layout string.
        layout_configs (list of LayoutConfig): Extraction strategies for each layout.
    """
    mode: ModeExtraction
    layout: LayoutExtraction
    layout_configs: List[LayoutConfig]

    @staticmethod
    def from_json(json_obj):
        return Config(
            mode=ModeExtraction.from_json(json_obj["mode"]),
            layout=LayoutExtraction.from_json(json_obj["layout"]),
            layout_configs=[
                LayoutConfig.from_json({name: deck_layouts}) for name, deck_layouts in json_obj["layout_configs"].items()
            ]
        )

    def get_current_layout(self, image) -> Optional[LayoutConfig]:
        """Extracts mode and layout and returns matching LayoutConfig."""
        mode_str = self.mode.extract_from_image(image)
        if mode_str != "PERFORMANCE":
            return None

        layout_str = self.layout.extract_from_image(image)
        for layout_obj in self.layout_configs:
            if layout_obj.name == layout_str:
                return layout_obj

        return None
