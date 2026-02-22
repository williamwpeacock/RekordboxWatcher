import pyautogui
import datetime
import json
import time
import numpy as np

from pydantic import model_serializer

from layout import load_from_json, Config
from snapshot import *

# Extracts data from rekordbox and tracks it using RekordboxRecording
class RekordboxWatcher(BaseModel):
    snapshots: List[Snapshot]

    config: Config
    num_decks: int
    output_dir: str

    recording_start_time: float

    def __init__(self, config_path: str = "bounding_boxes.json", output_dir: str = "out"):
        super().__init__(
            snapshots = [],
            config = load_from_json(config_path),
            num_decks = 4,
            output_dir = output_dir,
            recording_start_time = -1
        )

    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        d = handler(self)
        del d['config']
        return d

    def _save_recording(self):
        dt=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{self.output_dir}/mix_{dt}.json"

        print(f"Saved recording to: {file_name}")
        with open(file_name, "w") as f:
            f.write(
                json.dumps(
                    self.model_dump(mode="python"),
                    indent=4
                )
            )
        print("Done!")

    def _is_recording(self):
        return self.recording_start_time > 0

    def _start_recording(self, start_time: float):
        print("Starting recording...")
        self.recording_start_time = start_time
        self.snapshots = []

    def _record_snapshot(self, snapshot: Snapshot):
        snapshot.time.value -= self.recording_start_time
        self.snapshots.append(snapshot)

    def _stop_recording(self):
        self.recording_start_time = -1

    def _extract_deck_snapshot(self, deck_config, image):
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
            song=SongSnapshot(
                name=deck_config.song.extract_from_image(image),
                artist=deck_config.artist.extract_from_image(image)
            ),
            time=TimeSnapshot(
                value=deck_config.time.extract_from_image(image),
                unit="seconds"
            ),
            volume=volume,
            eq=EQSnapshot(high=0, medium=0, low=deck_config.eq.low.extract_from_image(image))
        )

    def _extract_snapshot(self, time):
        image = pyautogui.screenshot()
        layout = self.config.get_current_layout(image)
        if layout is None:
            return None

        snapshot = Snapshot(decks=[], bpm=-1, time=TimeSnapshot(value=time, unit="seconds"))

        for deck_config in layout.decks:
            snapshot.decks.append(self._extract_deck_snapshot(deck_config, image))

            if deck_config.is_master.extract_from_image(image):
                snapshot.bpm = deck_config.bpm.extract_from_image(image)

        if all([(deck is None) for deck in snapshot.decks]):
            return None

        return snapshot

    def look(self) -> Optional[Snapshot]:
        current_time = np.round(time.time(), 2)

        snapshot = self._extract_snapshot(current_time)
        if snapshot is None:
            if self._is_recording():
                self._stop_recording()
            return None

        if not self._is_recording():
            self._start_recording(current_time)

        self._record_snapshot(snapshot)

        return snapshot

    def watch(self, save = True):
        # wait to start
        while not self._is_recording():
            snapshot = self.look()

        # record
        while snapshot is not None:
            # handle timing
            snapshot = self.look()

        if save:
            self._save_recording()

        return self.snapshots

if __name__ == "__main__":
    watcher = RekordboxWatcher(
        config_path = "bounding_boxes.json",
        output_dir="out"
    )

    while True:
        watcher.watch(save = True)
