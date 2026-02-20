import json
import time
import numpy as np
import pyautogui

from pydantic import BaseModel
from typing import List, Optional, Tuple

from snapshot import *
from layout import Config, load_from_json
from helper_functions import *

# Basic recording of rekordbox
# contains list of states and key transition points
class RekordboxRecording(BaseModel):
    snapshots: List[Snapshot]

    # Metadata
    num_decks: int
    """Time (in seconds) into first song that recording started"""
    offset: float
    """snapshot indices where bpm change recorded"""
    bpm_changes: List[int]
    """snapshot indices where volume change recorded"""
    volume_changes: List[List[int]]
    """snapshot indices where new song starts playing"""
    song_starts: List[List[int]]
    """snapshot indices where song stops playing"""
    song_stops: List[List[int]]

    def __init__(self, num_decks):
        super().__init__(
            snapshots=[],
            num_decks = num_decks,
            offset = 0,
            bpm_changes = [],
            song_starts = [[] for _ in range(num_decks)],
            song_stops = [[] for _ in range(num_decks)],
            volume_changes = [[] for _ in range(num_decks)]
        )

    def get_recording_start(self):
        return self.snapshots[0].time.value

    def get_recording_offset(self):
        # check if first song still playing
        first_snapshot = self.snapshots[0]
        for i, deck in enumerate(first_snapshot.decks):
            if deck is not None:
                playing_deck_idx = i
        current_snapshot = self.snapshots[-1]

        if current_snapshot.decks[playing_deck_idx] is None or len(self.song_starts[playing_deck_idx]) > 1:
            return self.offset

        # find relevant bpm changes
        last_bpm_change = 0
        relevant_bpm_changes = []
        for change_idx in self.bpm_changes:
            if change_idx > len(self.snapshots):
                break
            relevant_bpm_changes.append(last_bpm_change)
            last_bpm_change = change_idx

        # get deck and mix times for all snapshots up to current one
        current_bpm_window = 0
        deck_times = []
        mix_times = []
        for snapshot_idx in range(0, len(self.snapshots)):
            if current_bpm_window < len(relevant_bpm_changes)-1 and snapshot_idx > relevant_bpm_changes[current_bpm_window + 1]:
                current_bpm_window += 1

            current_deck = self.snapshots[snapshot_idx].decks[playing_deck_idx]
            if current_deck is None:
                break

            deck_time = current_deck.time.value
            mix_time = self.snapshots[snapshot_idx].time.value
            if current_bpm_window == len(deck_times):
                deck_times.append([])
                mix_times.append([])

            if deck_time >= 0:
                deck_times[-1].append(deck_time)
                mix_times[-1].append(mix_time)

        # calculate original bpm and start point
        # bpms = []
        starts = []
        for bpm_window_idx, snapshot_idx in enumerate(relevant_bpm_changes):
            # mix_bpm = self.snapshots[snapshot_idx].bpm

            xs = mix_times[bpm_window_idx]
            ys = deck_times[bpm_window_idx]
            if len(xs) > 1 and len(ys) > 1:
                slope, intercept = np.polyfit(xs, ys, 1)
                # bpms.append(mix_bpm / slope)
                starts.append(-intercept / slope)

        if len(starts) == 0:
            # self.offset = self.snapshots[0].decks[playing_deck_idx].time.value
            # find valid song time in snapshots
            self.offset = 0
        else:
            self.offset = np.mean(starts) - self.snapshots[0].time.value

        return self.offset

    def append_snapshot(self, snapshot: Snapshot):
        self.snapshots.append(snapshot)
        snapshot_idx = len(self.snapshots) - 1

        update = False

        # check for bpm change
        if len(self.bpm_changes) == 0 or self.snapshots[self.bpm_changes[-1]].bpm != snapshot.bpm:
            self.bpm_changes.append(snapshot_idx)
            update = True

        for deck_idx, deck in enumerate(snapshot.decks):
            if deck is None:
                # check for song stop
                deck_song_starts = self.song_starts[deck_idx]
                deck_song_stops = self.song_stops[deck_idx]
                if len(deck_song_stops) != len(deck_song_starts):
                    self.song_stops[deck_idx].append(snapshot_idx)
                    update = True
                    continue

            # check for volume change
            deck_volume_changes = self.volume_changes[deck_idx]
            if len(deck_volume_changes) == 0 or self.snapshots[deck_volume_changes[-1]].decks[deck_idx].volume != deck.volume:
                self.volume_changes[deck_idx].append(snapshot_idx)
                update = True

            # check for song start
            deck_song_starts = self.song_starts[deck_idx]
            if len(deck_song_starts) == 0 or str(self.snapshots[deck_song_starts[-1]].decks[deck_idx].song) != str(deck.song):
                self.song_starts[deck_idx].append(snapshot_idx)
                update = True

        return update

    def export(self, file_path: str):
        print(f"Exporting mix to: {file_path}")
        with open(file_path, "w") as f:
            f.write(
                json.dumps(
                    self.model_dump(mode="python"),
                    indent=4
                )
            )
        print("Done!")

    @staticmethod
    def from_snapshots(snapshots: List[Snapshot], num_decks = 4):
        recording = RekordboxRecording(num_decks)

        for snapshot_idx, snapshot in enumerate(snapshots):
            recording.append_snapshot(snapshot)

        return recording

class RekordboxDeck(BaseModel):
    """song start points relative to mix start (bars) and song start (bars)"""
    song_starts: List[Tuple[float, float, SongSnapshot]]
    """volume change points relative to mix start (bars)"""
    volume_changes: List[Tuple[float, float]]

    def get_state(self, time_in_bars: float):
        current_song_offset = 0
        current_song = SongSnapshot(name="", artist="")
        for bar, song_bar, song in self.song_starts:
            if bar > time_in_bars:
                break
            current_song_offset = bar - song_bar
            current_song = song

        current_time = TimeSnapshot(
            value = time_in_bars - current_song_offset,
            unit = "bars"
        )

        last_volume_point = (0, 0)
        current_volume = 0
        for bar, volume in self.volume_changes:
            if bar > time_in_bars:
                current_volume = time_in_bars * (volume - last_volume_point[1]) / (bar - last_volume_point[0])
                break
            last_volume_point = (bar, volume)

        return DeckSnapshot(
            song=current_song,
            time=current_time,
            volume=current_volume,
            eq=EQSnapshot(high=0, medium=0, low=0)
        )

# Advanced recording of rekordbox
# all times in bars relative to mix start
# FUTURE WORK:
# contains implicit state of rekordbox from analysing RecordboxRecording
class RekordboxMix(BaseModel):
    recording: RekordboxRecording

    num_decks: int

    """bpm change points relative to mix start (bars)"""
    bpm_changes: List[Tuple[float, float]]
    """decks containing list of changes"""
    deck_changes: List[RekordboxDeck]

    def __init__(self, num_decks):
        super().__init__(
            recording = RekordboxRecording(num_decks),
            num_decks = num_decks,
            bpm_changes = [],
            deck_changes = [RekordboxDeck(song_starts=[], volume_changes=[]) for _ in range(num_decks)]
        )

    def stop(self):
        print("blah")
        print(self.bpm_changes)
        for deck in self.deck_changes:
            print(deck.song_starts)
            print(deck.volume_changes)
        self.recording.export("out/blah blah blah.json")

    def append_snapshot(self, snapshot):
        if self.recording.append_snapshot(snapshot):
            self._update()

    def get_state(self, time: TimeSnapshot) -> Snapshot:
        """Gets rekordbox state at time in mix by interpolating/extrapolating based on key points"""
        if time.unit == "seconds":
            time_in_bars = 0
            if len(self.recording.snapshots) > 0:
                time_in_bars = seconds_to_bars_with_changes(self.bpm_changes, time.value - self.recording.get_recording_start())
        elif time.unit == "bars":
            time_in_bars = time.value

        current_bpm = 0
        for bar, bpm in self.bpm_changes:
            if bar > time_in_bars:
                break
            current_bpm = bpm

        return Snapshot(
            decks=[deck.get_state(time_in_bars) for deck in self.deck_changes],
            bpm=current_bpm,
            time=TimeSnapshot(value=time_in_bars, unit="bars")
        )

    def _update(self):
        start_time = self.recording.get_recording_start()
        if len(self.bpm_changes) != len(self.recording.bpm_changes):
            snapshot = self.recording.snapshots[self.recording.bpm_changes[-1]]
            time = seconds_to_bars_with_changes(self.bpm_changes, snapshot.time.value - start_time)
            self.bpm_changes.append((time, snapshot.bpm))

        for idx, deck in enumerate(self.deck_changes):
            if len(deck.song_starts) != len(self.recording.song_starts[idx]):
                snapshot_idx = self.recording.song_starts[idx][-1]
                snapshot = self.recording.snapshots[snapshot_idx]
                time = seconds_to_bars_with_changes(self.bpm_changes, snapshot.time.value - start_time)
                deck.song_starts.append((time, snapshot.decks[idx].song))

            if len(deck.volume_changes) != len(self.recording.volume_changes[idx]):
                snapshot_idx = self.recording.volume_changes[idx][-1]
                snapshot = self.recording.snapshots[snapshot_idx]
                print(snapshot.time.value)
                print(start_time)
                print(snapshot.time.value - start_time)
                time = seconds_to_bars_with_changes(self.bpm_changes, snapshot.time.value - start_time)
                deck.volume_changes.append((time, snapshot.decks[idx].volume))

# Extracts data from rekordbox and tracks it using RekordboxRecording
class RekordboxWatcher:
    mix: Optional[RekordboxMix]
    config: Config

    num_decks: int

    def __init__(self):
        self.config = load_from_json("bounding_boxes.json")
        self.mix = None
        self.num_decks = 4

    def _start_mix(self, initial_state):
        self.mix = RekordboxMix(self.num_decks)

    def _stop_mix(self):
        self.mix.stop()
        self.mix = None

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

    def get_state(self) -> Optional[Snapshot]:
        current_time = np.round(time.time(), 2)

        snapshot = self._extract_snapshot(current_time)
        if snapshot is None:
            if self.mix is not None:
                self._stop_mix()
            return None

        if self.mix is None:
            self._start_mix(snapshot)
        else:
            self.mix.append_snapshot(snapshot)

        return self.mix.get_state(TimeSnapshot(value=current_time, unit="seconds"))

    def watch(self):
        while True:
            self.get_state()