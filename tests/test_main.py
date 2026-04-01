import os
import pytest
from PIL import Image

from rekordbox_watcher import RekordboxWatcher
from rekordbox_watcher.schema import *

TEST_DATA_PATH = f"{os.path.dirname(__file__)}/data"

@pytest.fixture
def watcher():
    return RekordboxWatcher()

def test_look_windows_1080p(watcher: RekordboxWatcher):
    img = Image.open(f"{TEST_DATA_PATH}/windows_1080p.png")
    assert watcher._extract_snapshot(0, img) == Snapshot(
        decks=[
            DeckSnapshot(
                song=SongIdentifier(
                    name='Kallisto',
                    artist='Camo & Krooked/Medus',
                    link_method="FUZZY"
                ),
                is_playing=True,
                time=Time(value=102.8, unit='seconds'),
                volume=1.0,
                eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)
            ),
            DeckSnapshot(
                song=SongIdentifier(
                    name='Ego',
                    artist='',
                    link_method="FUZZY"
                ),
                is_playing=False,
                time=Time(value=0.0, unit='seconds'),
                volume=0.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)
            ),
            DeckSnapshot(song=None, is_playing=False, time=Time(value=0.0, unit='seconds'), volume=0.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)),
            DeckSnapshot(song=None, is_playing=False, time=Time(value=0.0, unit='seconds'), volume=0.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0))
        ],
        bpm=175.0,
        time=Time(value=0, unit='seconds')
    )

def test_look_windows_720p(watcher: RekordboxWatcher):
    img = Image.open(f"{TEST_DATA_PATH}/windows_720p.png")
    assert watcher._extract_snapshot(0, img) == Snapshot(
        decks=[
            DeckSnapshot(
                song=SongIdentifier(
                    name='Kallisto',
                    artist='Camo & Krooked/Medus',
                    link_method="FUZZY"
                ),
                is_playing=True,
                time=Time(value=91.3, unit='seconds'),
                volume=1.0,
                eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)
            ),
            DeckSnapshot(
                song=SongIdentifier(
                    name='Ego',
                    artist='',
                    link_method="FUZZY"
                ),
                is_playing=False,
                time=Time(value=0.0, unit='seconds'),
                volume=0.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)
            ),
            DeckSnapshot(song=None, is_playing=False, time=Time(value=0.0, unit='seconds'), volume=0.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)),
            DeckSnapshot(song=None, is_playing=False, time=Time(value=0.0, unit='seconds'), volume=0.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0))
        ],
        bpm=175.0,
        time=Time(value=0, unit='seconds')
    )

def test_look_mac(watcher: RekordboxWatcher):
    img = Image.open(f"{TEST_DATA_PATH}/mac.png")
    assert watcher._extract_snapshot(0, img) == Snapshot(
        decks=[
            DeckSnapshot(
                song=SongIdentifier(
                    name='SNARE9',
                    artist='',
                    link_method="FUZZY"
                ),
                is_playing=False,
                time=Time(value=0.0, unit='seconds'),
                volume=0.0,
                eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)
            ),
            DeckSnapshot(
                song=SongIdentifier(
                    name='Demo Track 2',
                    artist='Loopmasters',
                    link_method="FUZZY"
                ),
                is_playing=True,
                time=Time(value=10.5, unit='seconds'),
                volume=1.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)
            ),
            DeckSnapshot(song=None, is_playing=False, time=Time(value=0.0, unit='seconds'), volume=0.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0)),
            DeckSnapshot(song=None, is_playing=False, time=Time(value=0.0, unit='seconds'), volume=0.0, eq=EQSnapshot(high=0.0, medium=0.0, low=0.0))
        ],
        bpm=120.0,
        time=Time(value=0, unit='seconds')
    )