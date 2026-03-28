from enum import Enum

from pydantic import BaseModel
from typing import List, Optional

class LinkMethod(str, Enum):
    FUZZY = 'FUZZY'
    EXACT = 'EXACT'
    SELF = 'SELF'

class SongIdentifier(BaseModel):
    """Representation of a basic song identifier"""

    name: str
    artist: str
    link_method: LinkMethod

class Time(BaseModel):
    value: float
    unit: str

class EQSnapshot(BaseModel):
    """Representation of the current EQ knob values"""

    high: float
    medium: float
    low: float

class DeckSnapshot(BaseModel):
    """Representation of the current state of a deck and it's mixer values"""

    song: Optional[SongIdentifier]
    is_playing: bool
    time: Time
    volume: float
    eq: EQSnapshot

class Snapshot(BaseModel):
    """Representation of the current state of rekordbox"""

    decks: List[DeckSnapshot]
    bpm: float
    time: Time
