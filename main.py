import pyautogui
import datetime
import json
import time
import psutil
import logging
import requests

from layout import load_from_json, Config, DeckConfig
from cc_core import Snapshot, DeckSnapshot, EQSnapshot, SongIdentifier, TimeSeconds

from typing import List, Optional

logger = logging.getLogger(__name__)

def is_rekordbox_running():
    return ("rekordbox.exe" in (p.name() for p in psutil.process_iter()))

class RekordboxWatcher:
    config: Config
    num_decks: int

    def __init__(self, config_path: str = "bounding_boxes.json"):
        logger.info(f"Creating RekordboxWatcher using config at: {config_path}")
        self.config = load_from_json(config_path)
        self.num_decks = 4

    def _extract_song(self, deck_config: DeckConfig, image) -> Optional[SongIdentifier]:
        is_loaded = deck_config.is_loaded.extract_from_image(image)
        if not is_loaded:
            return None

        return SongIdentifier(
            name=deck_config.song.extract_from_image(image),
            artist=deck_config.artist.extract_from_image(image)
        )

    def _extract_deck_snapshot(self, deck_config: DeckConfig, image, previous_deck_snapshot: DeckSnapshot = None) -> DeckSnapshot:
        is_playing = deck_config.is_playing.extract_from_image(image)
        if is_playing:
            # song can only change if deck is not playing unless deck reaches the end of song
            # in this case assume deck is paused before new song starts playing
            if previous_deck_snapshot is None:
                song = self._extract_song(deck_config, image)
            else:
                song = previous_deck_snapshot.song

            # check for mixer updates
            volume = deck_config.volume.extract_from_image(image)
            time = deck_config.time.extract_from_image(image)
            eq = EQSnapshot(high=0, medium=0, low=deck_config.eq.low.extract_from_image(image))
        else:
            # check for song changes
            song = self._extract_song(deck_config, image)

            # mixer updates don't matter if no song is playing
            volume = 0
            time = 0
            eq = EQSnapshot(high=0, medium=0, low=0)

        return DeckSnapshot(
            song=song,
            is_playing=bool(is_playing),
            time=TimeSeconds(value=time),
            volume=volume,
            eq=eq
        )

    def _extract_snapshot(self, time: float, previous_snapshot: Optional[Snapshot] = None) -> Optional[Snapshot]:
        image = pyautogui.screenshot()
        layout = self.config.get_current_layout(image)
        if layout is None:
            return None

        decks = []
        bpm = -1
        for i, deck_config in enumerate(layout.decks):
            previous_deck_snapshot = previous_snapshot.decks[i] if previous_snapshot is not None else None
            decks.append(self._extract_deck_snapshot(deck_config, image, previous_deck_snapshot))

            if bpm == -1 and deck_config.is_master.extract_from_image(image):
                bpm = deck_config.bpm.extract_from_image(image)

        # snapshot is considered empty if no songs loaded
        if all([(deck.song is None) for deck in decks]):
            return None

        return Snapshot(
            decks=decks,
            bpm=bpm,
            time=TimeSeconds(time)
        )

    def _transmit(self, api_endpoint: str, snapshot: Snapshot):
        try:
            requests.post(api_endpoint, json = snapshot.model_dump(mode="python"))
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error occurred when transmitting snapshot: {e}")

    def look(self, previous_snapshot: Optional[Snapshot] = None) -> Optional[Snapshot]:
        current_time = time.time()

        return self._extract_snapshot(current_time, previous_snapshot)

    def watch(self, api_endpoint = None) -> List[Snapshot]:
        snapshots: List[Snapshot] = []
        snapshot: Optional[Snapshot] = None

        logger.info(f"Starting watch process.")
        while is_rekordbox_running():
            snapshot = self.look(snapshot)
            if snapshot is not None:
                logger.info(f"Extracted snapshot: {snapshot}")
                if api_endpoint is not None:
                    self._transmit(api_endpoint, snapshot)
                else:
                    snapshots.append(snapshot)

        logger.info("No rekordbox process found.")

        return snapshots

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
                    prog='ProgramName',
                    description='What the program does',
                    epilog='Text at the bottom of help')

    parser.add_argument('--config_path', default="bounding_boxes.json")
    parser.add_argument('--api_endpoint', default=None)
    parser.add_argument('--output_dir', default="out/")
    args = parser.parse_args()

    logger.setLevel(logging.INFO)

    watcher = RekordboxWatcher(
        config_path = args.config_path
    )
    snapshots = watcher.watch(args.api_endpoint)

    if len(snapshots) > 0:
        dt = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"{args.output_dir}/session_{dt}.json"

        logger.info(f"Saving to: {output_path}")
        with open(output_path, "w") as f:
            f.write(
                json.dumps(
                    [snapshot.model_dump(mode="python") for snapshot in snapshots],
                    indent=4
                )
            )
        logger.info("Done!")
