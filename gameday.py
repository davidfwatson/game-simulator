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
    originBase: Optional[str]  # e.g., "1B", or None for batter
    start: Optional[str]  # e.g., "1B", or None for batter
    end: Optional[str]
    outBase: Optional[str]


class RunnerDetails(TypedDict):
    event: str
    eventType: str
    isOut: bool
    rbi: int
    playIndex: int


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
    code: str
    isStrike: bool
    type: PitchType


class PitchBreaks(TypedDict):
    spinRate: int


class PitchData(TypedDict):
    startSpeed: float
    breaks: PitchBreaks


class PlayEvent(TypedDict):
    index: int
    details: PitchDetails
    count: PitchEventCount
    pitchData: NotRequired[PitchData]


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


class Play(TypedDict):
    result: PlayResult
    about: PlayAbout
    count: PlayCount  # Post-play count
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