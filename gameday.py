"""
This module defines the data structures for MLB Gameday-style play events,
which are used as the canonical, structured output of the simulation engine.
"""
from typing import List, Literal, Optional, TypedDict, Dict

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


class HandInfo(TypedDict):
    code: str
    description: str


class PlayerDetail(TypedDict):
    id: int
    fullName: str
    link: str
    firstName: str
    lastName: str
    primaryNumber: str
    birthDate: str
    currentAge: int
    birthCity: str
    birthStateProvince: str
    birthCountry: str
    height: str
    weight: int
    active: bool
    primaryPosition: Position
    useName: str
    useLastName: str
    middleName: str
    boxscoreName: str
    gender: str
    isPlayer: bool
    isVerified: bool
    draftYear: int
    mlbDebutDate: str
    batSide: HandInfo
    pitchHand: HandInfo
    strikeZoneTop: float
    strikeZoneBottom: float


class GameData(TypedDict):
    teams: GameTeams
    players: Dict[str, PlayerDetail]
    venue: str
    weather: str
    umpires: List[str]


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
    player: "PlayerInfo"
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
    code: str
    isStrike: bool
    type: PitchType
    eventType: NotRequired[str]
    zone: NotRequired[int]


class PitchBreaks(TypedDict):
    spinRate: int


class PitchData(TypedDict):
    startSpeed: float
    breaks: PitchBreaks
    zone: NotRequired[int]


class HitData(TypedDict):
    launchSpeed: float
    launchAngle: float
    trajectory: str
    location: NotRequired[str]


class PlayEvent(TypedDict):
    index: int
    details: PitchDetails
    count: PitchEventCount
    pitchData: NotRequired[PitchData]
    hitData: NotRequired[HitData]
    isBunt: NotRequired[bool]


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


class BattingStats(TypedDict):
    flyOuts: int
    groundOuts: int
    airOuts: int
    runs: int
    doubles: int
    triples: int
    homeRuns: int
    strikeOuts: int
    baseOnBalls: int
    intentionalWalks: int
    hits: int
    hitByPitch: int
    atBats: int
    caughtStealing: int
    stolenBases: int
    groundIntoDoublePlay: int
    groundIntoTriplePlay: int
    plateAppearances: int
    totalBases: int
    rbi: int
    leftOnBase: int
    sacBunts: int
    sacFlies: int
    catchersInterference: int
    pickoffs: int
    popOuts: int
    lineOuts: int


class PitchingStats(TypedDict):
    flyOuts: int
    groundOuts: int
    airOuts: int
    runs: int
    doubles: int
    triples: int
    homeRuns: int
    strikeOuts: int
    baseOnBalls: int
    intentionalWalks: int
    hits: int
    hitByPitch: int
    atBats: int
    caughtStealing: int
    stolenBases: int
    numberOfPitches: int
    inningsPitched: str
    earnedRuns: int
    battersFaced: int
    outs: int
    balls: int
    strikes: int
    hitBatsmen: int
    balks: int
    wildPitches: int
    pickoffs: int
    rbi: int
    sacBunts: int
    sacFlies: int
    popOuts: int
    lineOuts: int


class FieldingStats(TypedDict):
    assists: int
    putOuts: int
    errors: int
    chances: int
    caughtStealing: int
    stolenBases: int
    passedBall: int
    pickoffs: int


class TeamStats(TypedDict):
    batting: BattingStats
    pitching: PitchingStats
    fielding: FieldingStats


class PlayerGameStats(TypedDict):
    batting: NotRequired[BattingStats]
    pitching: NotRequired[PitchingStats]
    fielding: NotRequired[FieldingStats]


class BoxscorePlayer(TypedDict):
    person: PlayerInfo
    jerseyNumber: str
    position: Position
    status: dict  # code, description
    parentTeamId: int
    battingOrder: Optional[str]
    stats: PlayerGameStats
    seasonStats: dict
    gameStatus: dict
    allPositions: List[Position]


class BoxscoreTeamInfo(TypedDict):
    id: int
    name: str
    abbreviation: str
    teamName: str


class BoxscoreTeam(TypedDict):
    team: BoxscoreTeamInfo
    teamStats: TeamStats
    players: Dict[str, BoxscorePlayer]
    batters: List[int]
    pitchers: List[int]
    bench: List[int]
    bullpen: List[int]
    battingOrder: List[int]
    info: List[dict]
    note: List[dict]


class BoxscoreTeams(TypedDict):
    away: BoxscoreTeam
    home: BoxscoreTeam


class Boxscore(TypedDict):
    teams: BoxscoreTeams
    officials: List[dict]
    info: List[dict]
    pitchingNotes: List[str]
    topPerformers: List[dict]


class LiveData(TypedDict):
    linescore: Linescore
    plays: Plays
    boxscore: Boxscore


# Top-level structure for the entire game output
class GamedayData(TypedDict):
    gameData: GameData
    liveData: LiveData
