from pydantic import BaseModel

from typing import List, Optional

class SongSnapshot(BaseModel):
    """Representation of a basic song identifier"""

    name: str
    artist: str

class TimeSnapshot(BaseModel):
    """Representation of a time value"""

    value: float
    unit: str

class EQSnapshot(BaseModel):
    """Representation of the current EQ knob values"""

    high: float
    medium: float
    low: float

class DeckSnapshot(BaseModel):
    """Representation of the current state of a deck and it's mixer values"""

    song: SongSnapshot
    time: TimeSnapshot
    volume: float
    eq: EQSnapshot

class Snapshot(BaseModel):
    """Representation of the current state of rekordbox"""

    decks: List[Optional[DeckSnapshot]]
    bpm: float
    time: TimeSnapshot
