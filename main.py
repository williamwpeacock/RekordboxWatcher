import pyautogui
import datetime
import json
import time
import numpy as np
import psutil
import logging

from layout import load_from_json, Config, DeckConfig
from snapshot import *

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

        song = SongSnapshot(
            name=deck_config.song.extract_from_image(image),
            artist=deck_config.artist.extract_from_image(image)
        )
        if song.name == "Not Loaded." and song.artist == "":
            return None

        return DeckSnapshot(
            song=song,
            time=TimeSnapshot(
                value=deck_config.time.extract_from_image(image),
                unit="seconds"
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
            time=TimeSnapshot(value=time, unit="seconds")
        )

    def look(self) -> Optional[Snapshot]:
        current_time = np.round(time.time(), 2)

        return self._extract_snapshot(current_time)

    def watch(self) -> List[Snapshot]:
        snapshots: List[Snapshot] = []

        logger.info(f"Starting watch process.")
        while is_rekordbox_running():
            snapshot = self.look()
            if snapshot is not None:
                snapshots.append(snapshot)
                logger.info(f"Extracted snapshot: {snapshot}")

        logger.info("No rekordbox process found.")

        return snapshots

if __name__ == "__main__":
    config_path = "bounding_boxes.json"
    output_dir = "out/"
    logging_level = logging.INFO

    logger.setLevel(logging_level)

    watcher = RekordboxWatcher(
        config_path = "bounding_boxes.json"
    )
    snapshots = watcher.watch()

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
