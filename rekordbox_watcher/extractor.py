from typing import List, Optional, Dict
from pydantic import BaseModel

from .extraction import *
from .scaler import ScaledAnchorPoints, Scaler, ScalerFactory
from .layout import Config, Platform
from .schema import Snapshot, DeckSnapshot, EQSnapshot, SongIdentifier, LinkMethod, Time

class DeckExtractor(BaseModel):
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

    def _extract_song(self, image: Image) -> Optional[SongIdentifier]:
        """Extracts song info from target deck if song is loaded.

        Args:
            deck_config (DeckConfig): Config object for target deck.
            image (Image): Screenshot of rekordbox.

        Returns:
            SongIdentifier, or None: SongIdentifier object if loaded, None if not.

            SongIdentifier instantiated with `link_method`: `LinkMethod.FUZZY` to
            tell the linker these values may not be fully accurate.
        """
        is_loaded = self.is_loaded.extract_from_image(image)
        if not is_loaded:
            return None

        return SongIdentifier(
            name=self.song.extract_from_image(image),
            artist=self.artist.extract_from_image(image),
            link_method=LinkMethod.FUZZY
        )

    def extract_deck_snapshot(self, image: Image, previous_deck_snapshot: DeckSnapshot = None) -> DeckSnapshot:
        """Extracts deck info from target deck.

        Attempts to use previous_deck_snapshot to optimise extraction.

        Args:
            deck_config (DeckConfig): Config object for target deck.
            image (Image): Screenshot of rekordbox.
            previous_deck_snapshot (DeckSnapshot, optional): DeckSnapshot from previous extraction.
                Defaults to None.

        Returns:
            DeckSnapshot: Contains all info for current deck.
        """
        is_playing = self.is_playing.extract_from_image(image)
        if is_playing:
            # song can only change if deck is not playing unless deck reaches the end of song
            # in this case assume deck is paused before new song starts playing
            if previous_deck_snapshot is None:
                song = self._extract_song(image)
            else:
                song = previous_deck_snapshot.song

            # check for mixer updates
            volume = self.volume.extract_from_image(image)
            time = self.time.extract_from_image(image)
            eq = EQSnapshot(high=0, medium=0, low=self.low.extract_from_image(image))
        else:
            # check for song changes
            song = self._extract_song(image)

            # mixer updates don't matter if no song is playing
            volume = 0
            time = 0
            eq = EQSnapshot(high=0, medium=0, low=0)

        return DeckSnapshot(
            song=song,
            is_playing=bool(is_playing),
            time=Time(value=time, unit="seconds"),
            volume=volume,
            eq=eq
        )

class Extractor(BaseModel):
    decks: List[DeckExtractor]

    def __init__(self, scaler: Scaler, deck_configs):
        super().__init__(decks=[])

        for deck_num, deck_config in enumerate(deck_configs):
            anchor_points = scaler.get_scaled_anchor_points(deck_num)
            self.decks.append(
                DeckExtractor(
                    anchor_points = anchor_points,
                    deck_config = deck_config
                )
            )

    def extract_snapshot(self, time: float, image: Image, previous_snapshot: Optional[Snapshot] = None) -> Optional[Snapshot]:
        """Extracts rekordbox info at current time.

        Attempts to optimise using previous_snapshot.

        Args:
            time (float): Current time.
            previous_snapshot (Snapshot, optional): Snapshot from previous extraction.
                Defaults to None.

        Returns:
            Snapshot, or None: Snapshot if rekordbox on screen and songs loaded,
                None if not.
        """
        deck_snapshots = []
        bpm = -1
        for i, deck in enumerate(self.decks):
            previous_deck_snapshot = previous_snapshot.decks[i] if previous_snapshot is not None else None
            deck_snapshots.append(deck.extract_deck_snapshot(deck, image, previous_deck_snapshot))

            if bpm == -1 and deck.is_master.extract_from_image(image):
                bpm = deck.bpm.extract_from_image(image)

        # snapshot is considered empty if no songs loaded
        if all([(deck.song is None) for deck in deck_snapshots]):
            return None

        return Snapshot(
            decks=deck_snapshots,
            bpm=bpm,
            time=Time(value=time, unit="seconds")
        )

class ExtractorFactory(BaseModel):
    """Get or create Extractor for screen width and layout."""
    config: Config
    scaler_factory: ScalerFactory
    _extractor_map: Dict[Scaler, Extractor]

    def __init__(self, config: Config):
        super().__init__(
            config = config,
            scaler_factory = ScalerFactory(
                config_defaults = config.config_defaults
            )
        )

    def _get_layout_config(self, scaler, image):
        mode_property = self.config.mode

        extraction_cls = mode_property.extraction_strategy
        mode = extraction_cls(
            bb=BoundingBox.from_json(mode_property.bb)
        )
        mode_str = mode.extract_from_image(image)
        if mode_str != "PERFORMANCE":
            return None

        layout_property = self.config.layout

        extraction_cls = layout_property.extraction_strategy
        layout = extraction_cls(
            bb=BoundingBox.from_json(layout_property.bb)
        )
        layout_str = layout.extract_from_image(image)
        if layout_str in self.config.layout_configs:
            return self.config.layout_configs[layout_str]

        return None

    def get_extractor(self, image) -> Extractor:
        current_width, current_height = image.size
        scaler = self.scaler_factory.get_scaler(current_width, current_height, Platform.detect())

        if not hasattr(self, "_extractor_map"):
            self._extractor_map = {}

        if scaler not in self._extractor_map:
            self._extractor_map[scaler] = {}

        layout_config = self._get_layout_config(scaler, image)
        layout_str = layout_config.name

        if layout_str not in self._extractor_map[scaler]:
            self._extractor_map[scaler][layout_str] = Extractor(scaler, layout_config.deck_configs)

        return self._extractor_map[scaler][layout_str]
