"""Extracts state of rekordbox as Snapshots.

Uses Optical Character Recognition to extract deck and mixer
values from a rekordbox session. Rekordbox must be the top window
on the primary monitor for the watcher to work.

Typical usage example:

  watcher = RekordboxWatcher()
  watcher.watch(api_endpoint="127.0.0.1:8000/incoming_snapshot")
"""
import pyautogui
import datetime
import json
import time
import psutil
import logging
import requests
import os
from PIL import Image

from .layout import load_from_json, Config
from .extraction import DeckExtractionStrategies, Platform
from .schema import Snapshot, DeckSnapshot, EQSnapshot, SongIdentifier, LinkMethod, Time

from enum import Enum
from typing import List, Optional

DEFAULT_CONFIG_PATH = f"{os.path.dirname(__file__)}/bounding_boxes.json"

logger = logging.getLogger(__name__)

def is_rekordbox_running():
    """Returns True if rekordbox.exe process found in process list."""
    return ("rekordbox.exe" in (p.name() for p in psutil.process_iter()))

class RekordboxWatcher:
    """Extracts state of rekordbox as Snapshots."""
    config: Config
    num_decks: int

    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        """Creates a new RekordboxWatcher using the config provided.

        Args:
            config_path (str): Path to JSON file containing bounding boxes.
        """
        logger.info(f"Creating RekordboxWatcher using config at: {config_path}")
        self.config = load_from_json(config_path)
        self.num_decks = 4

    def _extract_song(self, deck: DeckExtractionStrategies, image: Image) -> Optional[SongIdentifier]:
        """Extracts song info from target deck if song is loaded.

        Args:
            deck_config (DeckConfig): Config object for target deck.
            image (Image): Screenshot of rekordbox.

        Returns:
            SongIdentifier, or None: SongIdentifier object if loaded, None if not.

            SongIdentifier instantiated with `link_method`: `LinkMethod.FUZZY` to
            tell the linker these values may not be fully accurate.
        """
        is_loaded = deck.is_loaded.extract_from_image(image)
        if not is_loaded:
            return None

        return SongIdentifier(
            name=deck.song.extract_from_image(image),
            artist=deck.artist.extract_from_image(image),
            link_method=LinkMethod.FUZZY
        )

    def _extract_deck_snapshot(self, deck: DeckExtractionStrategies, image: Image, previous_deck_snapshot: DeckSnapshot = None) -> DeckSnapshot:
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
        is_playing = deck.is_playing.extract_from_image(image)
        if is_playing:
            # song can only change if deck is not playing unless deck reaches the end of song
            # in this case assume deck is paused before new song starts playing
            if previous_deck_snapshot is None:
                song = self._extract_song(deck, image)
            else:
                song = previous_deck_snapshot.song

            # check for mixer updates
            volume = deck.volume.extract_from_image(image)
            time = deck.time.extract_from_image(image)
            eq = EQSnapshot(high=0, medium=0, low=deck.low.extract_from_image(image))
        else:
            # check for song changes
            song = self._extract_song(deck, image)

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

    def _extract_snapshot(self, time: float, image: Image, previous_snapshot: Optional[Snapshot] = None) -> Optional[Snapshot]:
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
        extraction_strategies = self.config.get_extraction_strategies(image)
        if extraction_strategies is None:
            return None

        decks = []
        bpm = -1
        for i, deck in enumerate(extraction_strategies.decks):
            previous_deck_snapshot = previous_snapshot.decks[i] if previous_snapshot is not None else None
            decks.append(self._extract_deck_snapshot(deck, image, previous_deck_snapshot))

            if bpm == -1 and deck.is_master.extract_from_image(image):
                bpm = deck.bpm.extract_from_image(image)

        # snapshot is considered empty if no songs loaded
        if all([(deck.song is None) for deck in decks]):
            return None

        return Snapshot(
            decks=decks,
            bpm=bpm,
            time=Time(value=time, unit="seconds")
        )

    def _transmit(self, api_endpoint: str, snapshot: Snapshot):
        """Sends snapshot in POST request to api_endpoint.

        Args:
            api_endpoint (str): URL of API endpoint accepting snapshots.
            snapshot (Snapshot): Snapshot to send
        """
        try:
            requests.post(api_endpoint, json = snapshot.model_dump(mode="python"))
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error occurred when transmitting snapshot: {e}")

    def look(self, previous_snapshot: Optional[Snapshot] = None) -> Optional[Snapshot]:
        """Extracts current state of rekordbox.

        Args:
            previous_snapshot (Snapshot, optional): Snapshot from previous extraction.
                Defaults to None.

        Returns:
            Snapshot, or None: Snapshot if rekordbox on screen and songs loaded,
                None if not.
        """
        current_time = time.time()
        current_image = pyautogui.screenshot()

        return self._extract_snapshot(current_time, current_image, previous_snapshot)

    def watch(self, api_endpoint = None) -> List[Snapshot]:
        """Repeatedly extracts and transmits rekordbox state.

        Args:
            api_endpoint (str, optional): URL of API endpoint accepting snapshots.

        Returns:
            List of Snapshot: List of snapshots extracted.
        """
        snapshots: List[Snapshot] = []
        snapshot: Optional[Snapshot] = None

        logger.info(f"Starting watch process.")
        while is_rekordbox_running():
            snapshot = self.look(snapshot)
            if snapshot is not None:
                logger.info(f"Extracted snapshot: {snapshot}")
                print(snapshot)
                if api_endpoint is not None:
                    self._transmit(api_endpoint, snapshot)
                else:
                    snapshots.append(snapshot)

        logger.info("No rekordbox process found.")

        return snapshots

def main(logging_level, config_path, api_endpoint, output_dir):
    logger.setLevel(logging_level)

    watcher = RekordboxWatcher(
        config_path = config_path if config_path is not None else DEFAULT_CONFIG_PATH
    )
    snapshots = watcher.watch(api_endpoint)

    if len(snapshots) > 0:
        dt = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{output_dir}/session_{dt}.json"

        logger.info(f"Saving to: {output_path}")
        with open(output_path, "w") as f:
            f.write(
                json.dumps(
                    [snapshot.model_dump(mode="python") for snapshot in snapshots],
                    indent=4
                )
            )
        logger.info("Done!")
