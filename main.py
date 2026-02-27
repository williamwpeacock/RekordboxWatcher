import pyautogui
import datetime
import json
import time
import numpy as np
import psutil
import logging
import requests

from layout import load_from_json, Config, DeckConfig
from cc_core import Snapshot, DeckSnapshot, EQSnapshot, SongIdentifier, TimeSeconds

from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)

def is_rekordbox_running():
    return ("rekordbox.exe" in (p.name() for p in psutil.process_iter()))

class RekordboxWatcher(BaseModel):
    config: Config
    num_decks: int

    def __init__(self, config_path: str = "bounding_boxes.json"):
        logger.info(f"Creating RekordboxWatcher using config at: {config_path}")
        super().__init__(
            config = load_from_json(config_path),
            num_decks = 4
        )

    def _extract_deck_snapshot(self, deck_config: DeckConfig, image) -> Optional[DeckSnapshot]:
        is_playing = deck_config.is_playing.extract_from_image(image)
        if not is_playing:
            return None

        volume = deck_config.volume.extract_from_image(image)
        if volume == 0:
            return None

        song = SongIdentifier(
            name=deck_config.song.extract_from_image(image),
            artist=deck_config.artist.extract_from_image(image)
        )
        if song.name == "Not Loaded." and song.artist == "":
            return None

        return DeckSnapshot(
            song=song,
            time=TimeSeconds(
                value=deck_config.time.extract_from_image(image)
            ),
            volume=volume,
            eq=EQSnapshot(high=0, medium=0, low=deck_config.eq.low.extract_from_image(image))
        )

    def _extract_snapshot(self, time: float) -> Optional[Snapshot]:
        image = pyautogui.screenshot()
        layout = self.config.get_current_layout(image)
        if layout is None:
            return None

        decks = []
        bpm = -1
        for deck_config in layout.decks:
            decks.append(self._extract_deck_snapshot(deck_config, image))

            if deck_config.is_master.extract_from_image(image):
                bpm = deck_config.bpm.extract_from_image(image)

        if all([(deck is None) for deck in decks]):
            return None

        return Snapshot(
            decks=decks,
            bpm=bpm,
            time=TimeSeconds(time)
        )

    def _transmit(self, api_endpoint: str, snapshot: Snapshot):
        requests.post(api_endpoint, json = snapshot.model_dump(mode="python"))

    def look(self) -> Optional[Snapshot]:
        current_time = np.round(time.time(), 2)

        return self._extract_snapshot(current_time)

    def watch(self, api_endpoint = None) -> List[Snapshot]:
        snapshots: List[Snapshot] = []

        logger.info(f"Starting watch process.")
        while is_rekordbox_running():
            snapshot = self.look()
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
