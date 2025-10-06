from typing import List, Literal, Optional, TypedDict

class Player(TypedDict):
    id: int

class Position(TypedDict):
    code: str
    name: str
    abbreviation: str

class Credit(TypedDict):
    player: Player
    position: Position
    credit: Literal["assist", "putout", "pickoff"]

class RunnerMovement(TypedDict):
    originBase: Optional[str]
    start: Optional[str]
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
    credits: List[Credit]

class PlayResult(TypedDict):
    type: str
    event: str
    eventType: str
    description: str
    rbi: int
    awayScore: int
    homeScore: int

class About(TypedDict):
    atBatIndex: int
    halfInning: Literal["top", "bottom"]
    isTopInning: bool
    inning: int
    isScoringPlay: bool

class Count(TypedDict):
    balls: int
    strikes: int
    outs: int

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
    count: Count
    pitchData: PitchData

class Play(TypedDict):
    result: PlayResult
    about: About
    count: Count
    playEvents: List[PlayEvent]
    runners: List[Runner]

class TeamInfo(TypedDict):
    id: int
    name: str
    abbreviation: str
    teamName: str

class Teams(TypedDict):
    away: TeamInfo
    home: TeamInfo

class GameData(TypedDict):
    teams: Teams

class LinescoreInning(TypedDict):
    num: int
    ordinalNum: str
    away: dict
    home: dict

class LinescoreTeams(TypedDict):
    away: dict
    home: dict

class Linescore(TypedDict):
    currentInning: int
    currentInningOrdinal: str
    inningState: str
    isTopInning: bool
    scheduledInnings: int
    outs: int
    balls: int
    strikes: int
    teams: LinescoreTeams
    innings: List[LinescoreInning]

class LiveData(TypedDict):
    linescore: Linescore
    plays: dict

class Gameday(TypedDict):
    gameData: GameData
    liveData: LiveData