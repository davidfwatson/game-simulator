"""
This module defines the data structures for MLB Gameday-style play events,
which are used as the canonical, structured output of the simulation engine.
"""
from typing import List, Literal, Optional, TypedDict

from typing_extensions import NotRequired


# Player/Team Structures
class PlayerReference(TypedDict):
    id: int


class Position(TypedDict):
    code: str
    name: str
    abbreviation: str


class TeamInfo(TypedDict):
    id: int
    name: str
    abbreviation: str
    teamName: str


class GameTeams(TypedDict):
    away: TeamInfo
    home: TeamInfo


class GameData(TypedDict):
    teams: GameTeams


# Linescore Structures
class TeamLinescore(TypedDict):
    runs: int
    hits: int
    errors: int
    leftOnBase: int


class InningLinescore(TypedDict):
    num: int
    ordinalNum: str
    away: TeamLinescore
    home: TeamLinescore


class LinescoreTeams(TypedDict):
    away: TeamLinescore
    home: TeamLinescore


class Linescore(TypedDict):
    scheduledInnings: int
    currentInning: int
    currentInningOrdinal: str
    inningState: str
    isTopInning: bool
    balls: int
    strikes: int
    outs: int
    teams: LinescoreTeams
    innings: List[InningLinescore]


# Play-by-Play Structures
class FielderCredit(TypedDict):
    player: PlayerReference
    position: Position
    credit: Literal["assist", "putout", "fielding_error"]


class RunnerMovement(TypedDict):
    originBase: Optional[str]  # "1B", "2B", "3B", or None for batter
    start: Optional[str]       # "1B", "2B", "3B", or None for batter
    end: Optional[str]         # "1B", "2B", "3B", "score", or None if out
    outBase: Optional[str]     # "1B", "2B", "3B", or None
    isOut: bool
    outNumber: Optional[int]   # 1, 2, or 3


class RunnerDetails(TypedDict):
    event: str                 # "Single", "Groundout", etc.
    eventType: str             # "single", "field_out", etc.
    movementReason: Optional[str]  # "r_adv_play", "r_force_out", "r_adv_force", etc.
    runner: "PlayerInfo"         # Full player info with id, fullName, link
    responsiblePitcher: NotRequired["PlayerInfo"]  # Only when runner scores
    isScoringEvent: bool
    rbi: bool
    earned: bool
    teamUnearned: bool
    playIndex: int             # Index of the pitch/event that caused movement


class Runner(TypedDict):
    movement: RunnerMovement
    details: RunnerDetails
    credits: List[FielderCredit]


class PitchEventCount(TypedDict):
    balls: int
    strikes: int


class PitchType(TypedDict):
    code: str
    description: str


class PitchDetails(TypedDict):
    description: str
    code: NotRequired[str]
    isStrike: NotRequired[bool]
    type: NotRequired[PitchType]
    eventType: NotRequired[str]
    # For action events
    event: NotRequired[str]
    isOut: NotRequired[bool]


class PitchBreaks(TypedDict):
    spinRate: int


class PitchData(TypedDict):
    startSpeed: float
    breaks: PitchBreaks


class HitData(TypedDict):
    launchSpeed: float
    launchAngle: float
    trajectory: str


class PlayEvent(TypedDict):
    index: int
    details: PitchDetails
    count: PitchEventCount
    pitchData: NotRequired[PitchData]
    hitData: NotRequired[HitData]
    isBunt: NotRequired[bool]
    # For action events
    isPitch: NotRequired[bool]
    type: NotRequired[str] # 'pitch' or 'action'
    isBaseRunningPlay: NotRequired[bool]


class PlayResult(TypedDict):
    type: str  # "atBat"
    event: str  # e.g., "Groundout"
    eventType: str  # e.g., "groundout"
    description: str
    rbi: int
    awayScore: int
    homeScore: int


class PlayAbout(TypedDict):
    atBatIndex: int
    halfInning: Literal["top", "bottom"]
    isTopInning: bool
    inning: int
    isScoringPlay: bool


class PlayCount(TypedDict):
    balls: int
    strikes: int
    outs: int


class PlayerInfo(TypedDict):
    id: int
    fullName: str
    link: str


class HandInfo(TypedDict):
    code: str
    description: str


class Splits(TypedDict):
    batter: str
    pitcher: str
    menOnBase: str


class Matchup(TypedDict):
    batter: PlayerInfo
    batSide: HandInfo
    pitcher: PlayerInfo
    pitchHand: HandInfo
    batterHotColdZones: List
    pitcherHotColdZones: List
    splits: Splits
    postOnFirst: NotRequired[PlayerInfo]
    postOnSecond: NotRequired[PlayerInfo]
    postOnThird: NotRequired[PlayerInfo]


class Play(TypedDict):
    result: PlayResult
    about: PlayAbout
    count: PlayCount  # Post-play count
    matchup: Matchup
    playEvents: List[PlayEvent]
    runners: List[Runner]


class Plays(TypedDict):
    allPlays: List[Play]


class LiveData(TypedDict):
    linescore: Linescore
    plays: Plays


# Top-level structure for the entire game output
class GamedayData(TypedDict):
    gameData: GameData
    liveData: LiveData