import pyautogui
import datetime
import json
import time
import numpy as np

from layout import load_from_json
from snapshot import *

def extract_deck_snapshot(deck_config, image):
    is_playing = deck_config.is_playing.extract_from_image(image)
    if not is_playing:
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
        volume=deck_config.volume.extract_from_image(image),
        eq=EQSnapshot(high=0, medium=0, low=deck_config.eq.low.extract_from_image(image))
    )

def extract_snapshot(config, image, time):
    layout = config.get_current_layout(image)
    if layout is None:
        return None

    snapshot = Snapshot(decks=[], bpm=-1, time=TimeSnapshot(value=time, unit="seconds"))

    for deck_config in layout.decks:
        snapshot.decks.append(extract_deck_snapshot(deck_config, image))

        if deck_config.is_master.extract_from_image(image):
            snapshot.bpm = deck_config.bpm.extract_from_image(image)

    if all([(deck is None) for deck in snapshot.decks]):
        return None

    return snapshot

def export_snapshots(snapshots):
    dt=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    file_name = f"out/mix_{dt}.json"

    print(f"Exporting mix to: {file_name}")
    with open(file_name, "w") as f:
        f.write(
            json.dumps(
                [snapshot.model_dump(mode="python") for snapshot in snapshots],
                indent=4
            )
        )
    print("Done!")

if __name__ == "__main__":
    config = load_from_json("bounding_boxes.json")

    snapshots = []
    while True:
        current_time = np.round(time.time(), 2)
        if len(snapshots) == 0:
            start_time = current_time

        image = pyautogui.screenshot()
        snapshot = extract_snapshot(config, image, current_time-start_time)

        if snapshot is not None:
            if current_time == start_time:
                print("Starting snapshot collection...")
            snapshots.append(snapshot)
        else:
            if len(snapshots) > 0:
                export_snapshots(snapshots)
                snapshots = []
            else:
                print("No snapshot taken")
