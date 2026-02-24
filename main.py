import pyautogui
import datetime
import json
import time
import numpy as np

from pydantic import model_serializer

from layout import load_from_json, Config
from snapshot import *

def get_date_time_str():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def save(output_path, content):
        print(f"Saved to: {output_path}")
        with open(output_path, "a") as f:
            f.write(
                json.dumps(
                    content,
                    indent=4
                )
            )
        print("Done!")

# Extracts data from rekordbox and tracks it using RekordboxRecording
class RekordboxWatcher(BaseModel):
    snapshots: List[Snapshot]
    recording_start_time: float

    config: Config
    num_decks: int
    output_path: str
    is_recording: bool

    def __init__(self, config_path: str = "bounding_boxes.json", output_dir: str = "out"):
        dt=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"recording_{dt}.json"

        super().__init__(
            snapshots = [],
            recording_start_time = -1,
            config = load_from_json(config_path),
            num_decks = 4,
            output_path = f"{output_dir}/{file_name}",
            is_recording = False
        )

    @model_serializer(mode="wrap")
    def _serialize(self, handler):
        d = handler(self)
        del d['config']
        del d['output_path']
        del d['is_recording']
        return d

    def _save_recording(self):
        save(self.output_path, self.model_dump(mode="python"))

    def _start_recording(self, start_time: float):
        print("Starting recording...")
        self.recording_start_time = start_time
        self.snapshots = []
        self.is_recording = True

    def _record_snapshot(self, snapshot: Snapshot):
        snapshot.time.value -= self.recording_start_time
        self.snapshots.append(snapshot)

    def _stop_recording(self):
        print("Stopping recording...")
        self.is_recording = False

    def _extract_deck_snapshot(self, deck_config, image, last_deck_snapshot: DeckSnapshot):
        is_playing = deck_config.is_playing.extract_from_image(image)
        if not is_playing:
            return None

        volume = deck_config.volume.extract_from_image(image)
        if volume == 0:
            return None

        song = SongSnapshot(
            name=deck_config.song.extract_from_image(image),
            artist=deck_config.artist.extract_from_image(image)
        ) if last_deck_snapshot is None else last_deck_snapshot.song
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

    def _extract_snapshot(self, time):
        image = pyautogui.screenshot()
        layout = self.config.get_current_layout(image)
        if layout is None:
            return None

        last_snapshot = self.snapshots[-1] if self.is_recording else None

        decks = []
        bpm = -1
        for deck_idx, deck_config in enumerate(layout.decks):
            last_deck_snapshot = last_snapshot.decks[deck_idx] if last_snapshot is not None else None
            decks.append(self._extract_deck_snapshot(deck_config, image, last_deck_snapshot))

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

        snapshot = self._extract_snapshot(current_time)
        if snapshot is None:
            if self.is_recording:
                self._stop_recording()
            return None

        if not self.is_recording:
            self._start_recording(current_time)

        self._record_snapshot(snapshot)

        return snapshot

    def watch(self, save = True) -> List[Snapshot]:
        # wait to start
        while not self.is_recording:
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
