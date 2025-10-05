"""
Data classes for MLB Gameday play events, based on gameday_schema.yml.
"""
from typing import List, Literal, Optional, TypedDict, Union


# ---------------------------
# Alignment snapshots
# ---------------------------
class PlayerRef(TypedDict):
    id: int
    link: Optional[str]


class AlignmentDefense(TypedDict, total=False):
    pitcher: PlayerRef
    catcher: PlayerRef
    first: PlayerRef
    second: PlayerRef
    third: PlayerRef
    shortstop: PlayerRef
    left: PlayerRef
    center: PlayerRef
    right: PlayerRef


class AlignmentOffense(TypedDict, total=False):
    batter: PlayerRef
    first: PlayerRef
    second: PlayerRef
    third: PlayerRef


# ---------------------------
# Flags
# ---------------------------
class Flag(TypedDict):
    flag: str
    value: Union[bool, str, int]


# ---------------------------
# Hit Data
# ---------------------------
class HitCoordinates(TypedDict):
    coordX: float
    coordY: float


class HitData(TypedDict, total=False):
    launchSpeed: float
    launchAngle: float
    totalDistance: float
    trajectory: str  # e.g., ground_ball, line_drive, fly_ball, popup
    hardness: str  # e.g., soft, medium, hard
    location: int
    coordinates: HitCoordinates


# ---------------------------
# Pitch Data
# ---------------------------
class PitchCoordinates(TypedDict, total=False):
    aX: float
    aY: float
    aZ: float
    pfxX: float
    pfxZ: float
    pX: float
    pZ: float
    vX: float
    vY: float
    vZ: float
    x: float
    y: float
    x0: float
    y0: float
    z0: float


class PitchBreaks(TypedDict, total=False):
    breakAngle: float
    breakLength: float
    breakY: float
    spinRate: int
    spinDirection: int
    zone: int
    typeConfidence: float


class PitchData(TypedDict, total=False):
    startSpeed: float
    endSpeed: float
    strikeZoneTop: float
    strikeZoneBottom: float
    nastyFactor: float
    coordinates: PitchCoordinates
    breaks: PitchBreaks


# ---------------------------
# Core Play Event
# ---------------------------
class Count(TypedDict):
    balls: int
    strikes: int


class DetailsCall(TypedDict):
    code: str
    description: str


class DetailsType(TypedDict):
    code: str  # e.g., FF, SL, CU, SI, KC, CH, etc.
    description: str  # e.g., Four-Seam Fastball


class Details(TypedDict, total=False):
    description: str
    code: str
    event: str
    isInPlay: bool
    isStrike: bool
    isBall: bool
    hasReview: bool
    ballColor: str
    trailColor: str
    call: DetailsCall
    type: DetailsType


class PlayEventType(TypedDict):
    code: str  # One of Pitch, Pickoff, Action
    description: Optional[str]


class PlayEvent(TypedDict, total=False):
    index: int
    pfxId: str
    playId: str
    atBatIndex: int
    pitchNumber: int
    isPitch: bool
    type: PlayEventType
    details: Details
    count: Count
    pitchData: PitchData
    hitData: HitData
    flags: List[Flag]
    defense: AlignmentDefense
    offense: AlignmentOffense

# The top-level object is a list of play events
GamedayPlayEvents = List[PlayEvent]