#!/usr/bin/env python3
"""Blind realism test: can a reader tell our generated games from real ones?

Builds triplets of play-by-play excerpts (one inning by default, --innings N), all rendered by our
narrative engine with our own team, player and venue names:

  real  - a real MLB game (StatsAPI live feed, anonymized)
  sleep - a hand-written Sleep Baseball game (transcript fixture, rendered with
          its fitted draws so the wording follows the original broadcast)
  sim   - a game from our simulator with a fresh random seed

Each triplet is written as A.txt/B.txt/C.txt in shuffled order plus key.json.
A judge (a fresh model with only the three texts) labels them; score() tallies
accuracy against the 1-in-6 chance of guessing all three.

    python blind_judge.py build --out DIR --count 12 --real-feeds 'feeds/*.json'
    python blind_judge.py score --out DIR      # after judges write answer.json
"""

import argparse
import copy
import glob
import json
import random
import re
from pathlib import Path

from anonymize_real_gameday import anonymize_gameday_data
from baseball import BaseballSimulator
from renderers import NarrativeRenderer
from teams import TEAMS

ROOT = Path(__file__).resolve().parent
FIXTURE_DIR = ROOT / "examples" / "transcript_games"
# The six newest complete episodes (Dec 2025 - Aug 2026; 052/053 postdate the
# judge's training cutoff). Three made every hand-written excerpt carry the
# same source tells round after round.
SLEEP_EPISODES = ("045", "046", "049", "050", "052", "053")
HOME, AWAY = "BAY_BOMBERS", "PC_PILOTS"
# Extra players (relievers, pinch hitters) beyond our 13-man rosters. Invented
# names only: the other TEAMS rosters are full of real MLB players (Ricky
# Henderson, Jason Giambi, Corbin Carroll), which a judge reads as a leak.
OVERFLOW = {
    "home": ["Dale Whitcomb", "Ray Pellerin", "Tommy Askew", "Luis Ocampo", "Brent Haddix",
             "Curtis Vane", "Mel Strand", "Danny Ruehl", "Hector Lasso", "Gil Marchetti",
             "Wade Kimbrell", "Nico Ferrante", "Jay Tolliver", "Ozzie Quill", "Russ Delacroix"],
    "away": ["Earl Brannock", "Sid Fennimore", "Rafael Cuenca", "Lyle Gessner", "Mickey Dorr",
             "Arturo Velez", "Hal Pruitt", "Kip Lindqvist", "Doug Sarratt", "Benny Ochoa",
             "Clay Rourke", "Manny Ybarra", "Glen Hutchins", "Theo Brakefield", "Abe Calloway"],
}

SPLIT_RE = re.compile(r"^\[TTS SPLIT HERE DELAY:([\d.]+)s\]$")
BACK_RE = re.compile(r"\s*(And )?[Ww]e'll be (right )?back\b[^.]*\.")
STATION_RE = re.compile(r"\s*Here on [^.]*\bNetwork\.")
RETURN_RE = re.compile(r"^(And )?(welcome back|we're back)\b[^.]*\.\s*", re.I)

JUDGE_PROMPT = """Below are three excerpts of baseball radio play-by-play, labelled A, B and C. Each covers the same stretch of {span}.

Exactly one is from a REAL Major League game. One is from a HAND-WRITTEN fictional game (a writer invented the game for a sleep-story podcast). One is from a COMPUTER SIMULATION of a game. Team, player and ballpark names have been replaced with the same fictional names in all three, and all three were turned into prose by the same commentary engine, so wording style alone won't separate them: look at what happens in the game.

Do not use any tools. Answer with only a JSON object:
{"A": "real|handwritten|simulated", "B": "...", "C": "...", "confidence": <0-1>, "tells": [{"excerpt": "A|B|C", "quote": "<exact line>", "why": "<one sentence>"}]}

Give 2-5 tells, quoting the lines that most gave each excerpt away.

=== A ===
{A}

=== B ===
{B}

=== C ===
{C}
"""


# ---------------------------------------------------------------- sources

def sim_game(seed):
    game = BaseballSimulator(TEAMS[HOME], TEAMS[AWAY], game_seed=seed)
    game.play_game()
    return game.gameday_data


def sleep_game(episode):
    return json.loads((FIXTURE_DIR / f"episode_{episode}.json").read_text())


def real_game(path, seed):
    import anonymize_real_gameday as anon
    raw = json.loads(Path(path).read_text())
    captured = {}
    original = anon.create_player_mapping

    def capture(real_data, our_teams):
        id_mapping, name_mapping = original(real_data, our_teams)
        captured.update(id_mapping)
        return id_mapping, name_mapping

    anon.create_player_mapping = capture
    try:
        data = anonymize_gameday_data(raw, TEAMS, seed=seed)
    finally:
        anon.create_player_mapping = original
    players = {p["id"]: p for p in data["gameData"]["players"].values()}
    # The anonymizer hands each real player a random one of ours, position
    # and all; put the real positions back so a shortstop isn't announced as
    # "the pitcher".
    for real in raw["gameData"]["players"].values():
        ours = captured.get(real["id"])
        if ours and ours["id"] in players and real.get("primaryPosition"):
            players[ours["id"]]["primaryPosition"] = real["primaryPosition"]
    # The anonymizer reduces player references to bare ids; the renderer
    # needs names on them.
    for play in data["liveData"]["plays"]["allPlays"]:
        for role in ("batter", "pitcher"):
            ref = play["matchup"].get(role)
            if ref and "fullName" not in ref and ref.get("id") in players:
                ref["fullName"] = players[ref["id"]]["fullName"]
    _fill_names(data, players)
    return data


def _fill_names(node, players):
    if isinstance(node, dict):
        if "id" in node and "fullName" not in node and node["id"] in players and len(node) <= 3:
            node["fullName"] = players[node["id"]]["fullName"]
        for value in node.values():
            _fill_names(value, players)
    elif isinstance(node, list):
        for value in node:
            _fill_names(value, players)


# ---------------------------------------------------------------- names

def player_sides(data):
    """Which team each player id played for, from who batted/pitched when."""
    sides = {}
    for play in data["liveData"]["plays"]["allPlays"]:
        top = play["about"]["isTopInning"]
        batter, pitcher = play["matchup"]["batter"], play["matchup"]["pitcher"]
        sides.setdefault(batter["id"], "away" if top else "home")
        sides.setdefault(pitcher["id"], "home" if top else "away")
    return sides


def remap_names(data, template_game_data):
    """Give every player, team and the venue our names, consistently."""
    data = copy.deepcopy(data)
    players = data["gameData"]["players"]
    by_id = {p["id"]: p for p in players.values()}
    sides = player_sides(data)
    # Only players who appear in the plays need names; a real feed's
    # gameData.players also lists the whole bench.
    referenced = []

    def collect(node):
        if isinstance(node, dict):
            if node.get("id") in by_id:
                referenced.append(node["id"])
            for v in node.values():
                collect(v)
        elif isinstance(node, list):
            for v in node:
                collect(v)

    collect(data["liveData"])
    order = list(dict.fromkeys(
        [ref["id"] for play in data["liveData"]["plays"]["allPlays"]
         for ref in (play["matchup"]["batter"], play["matchup"]["pitcher"])] + referenced))
    for pid in order:
        sides.setdefault(pid, "home")
    ours = [p["legal_name"] for key in (HOME, AWAY) for p in TEAMS[key]["players"]]
    firsts = [n.split()[0] for n in ours]
    lasts = [n.split()[-1] for n in ours]
    taken = {p["legal_name"] for t in TEAMS.values() for p in t["players"]}
    invented = (f"{f} {l}" for i, f in enumerate(firsts) for l in lasts[i + 7:] + lasts[:i + 7]
                if f"{f} {l}" not in taken)

    id_names = {}
    for side, key in (("home", HOME), ("away", AWAY)):
        roster = [p["legal_name"] for p in TEAMS[key]["players"]]
        pos = {p["legal_name"]: p["position"]["code"] for p in TEAMS[key]["players"]}
        spare = list(OVERFLOW[side])
        free = list(roster)
        for pid in order:
            if sides[pid] != side:
                continue
            code = (by_id[pid].get("primaryPosition") or {}).get("code")
            pick = next((n for n in free if pos[n] == code), None)
            if pick is None:
                hitters = [n for n in free if pos[n] != "1"] if code != "1" else []
                pick = (hitters or [n for n in free if code == "1" and pos[n] == "1"] or [None])[0]
            if pick is None:
                pick = spare.pop(0) if spare else next(invented)
            else:
                free.remove(pick)
            id_names[pid] = pick

    # Anyone else in the player table (a fielder only named in a credit the
    # walk above missed, a bench player) still carries the anonymizer's
    # placeholder, which is one of OUR roster names ("Power" fielding for the
    # Bombers while Rex Power bats for the Pilots). Give them invented names.
    used = set(id_names.values())
    for pid in by_id:
        if pid not in id_names:
            name = next(n for n in invented if n not in used)
            id_names[pid] = name
            used.add(name)

    # Structured references are renamed by player id. The anonymizer can give
    # two real players the same placeholder name, so a name-keyed map sent a
    # Pilots reliever out as "Leo Vance". Free text is only rewritten for
    # placeholder names that belong to exactly one player.
    name_counts = {}
    for pid in id_names:
        name_counts[by_id[pid]["fullName"]] = name_counts.get(by_id[pid]["fullName"], 0) + 1
    mapping = {by_id[pid]["fullName"]: new for pid, new in id_names.items()
               if name_counts[by_id[pid]["fullName"]] == 1}
    full = sorted(mapping, key=len, reverse=True)

    def swap(text):
        for old in full:
            text = re.sub(rf"\b{re.escape(old)}\b", mapping[old], text)
        return text

    def walk(node):
        if isinstance(node, dict):
            new = id_names.get(node.get("id")) if "fullName" in node else None
            if new is None and "fullName" in node:
                new = mapping.get(node["fullName"])
            if new:
                node["fullName"] = new
                first, _, last = new.partition(" ")
                for k in ("lastName", "useLastName", "boxscoreName"):
                    if k in node:
                        node[k] = last
                for k in ("firstName", "useName"):
                    if k in node:
                        node[k] = first
            for k, v in node.items():
                if isinstance(v, str) and k not in ("fullName",):
                    node[k] = swap(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                if isinstance(v, str):
                    node[i] = swap(v)
                else:
                    walk(v)

    walk(data["liveData"])
    walk(players)

    gd = data["gameData"]
    gd["teams"] = copy.deepcopy(template_game_data["teams"])
    gd["venue"] = template_game_data["venue"]
    broadcast = gd.get("broadcast") or {}
    for k in ("network_name", "station_call"):
        broadcast.pop(k, None)
    if broadcast:
        gd["broadcast"] = broadcast
    return data


# ---------------------------------------------------------------- rendering

def render(data, seed=None):
    if "commentaryRng" in data.get("gameData", {}):
        return NarrativeRenderer(data).render()
    return NarrativeRenderer(data, seed=seed).render()


def inning_excerpt(text, inning, span=1):
    """`span` full innings from `inning`, without TTS markers or commercial-break lines."""
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if "we are underway" in l.lower())
    halves, current = [], []
    for line in lines[start + 1:]:
        m = SPLIT_RE.match(line.strip())
        if m and float(m.group(1)) == 15.0:
            halves.append(current)
            current = []
        else:
            current.append(line)
    halves.append(current)
    out = []
    for half in halves[2 * inning - 2: 2 * (inning + span - 1)]:
        for line in half:
            line = line.strip()
            if not line or SPLIT_RE.match(line):
                continue
            line = STATION_RE.sub("", BACK_RE.sub("", line))
            line = RETURN_RE.sub("", line).strip()
            if line:
                out.append(line)
        out.append("")
    return "\n".join(out).strip() + "\n"


def innings_played(data):
    return max(p["about"]["inning"] for p in data["liveData"]["plays"]["allPlays"])


# ---------------------------------------------------------------- build/score

def build(out, count, real_feeds, seed, span=1):
    rng = random.Random(seed)
    template = sim_game(1)["gameData"]
    feeds = sorted(glob.glob(real_feeds))
    if not feeds:
        raise SystemExit(f"no real feeds match {real_feeds}")
    out = Path(out)
    for n in range(1, count + 1):
        episode = SLEEP_EPISODES[(n - 1) % len(SLEEP_EPISODES)]
        feed = feeds[(n - 1) % len(feeds)]
        sim_seed = rng.randrange(1, 10 ** 6)
        sources = {
            "sleep": remap_names(sleep_game(episode), template),
            "real": remap_names(real_game(feed, seed=sim_seed), template),
            "sim": sim_game(sim_seed),
        }
        last = min(9, *(innings_played(d) for d in sources.values())) - span + 1
        inning = rng.randint(1, max(1, min(last, 9 - span)))
        texts = {k: inning_excerpt(render(d, seed=sim_seed), inning, span) for k, d in sources.items()}
        labels = ["A", "B", "C"]
        kinds = list(texts)
        rng.shuffle(kinds)
        tdir = out / f"triplet_{n:02d}"
        tdir.mkdir(parents=True, exist_ok=True)
        key = {}
        for label, kind in zip(labels, kinds):
            (tdir / f"{label}.txt").write_text(texts[kind])
            key[label] = kind
        (tdir / "key.json").write_text(json.dumps({
            "key": key, "inning": inning, "span": span, "sleep_episode": episode,
            "real_feed": Path(feed).name, "sim_seed": sim_seed}, indent=1))
        prompt = JUDGE_PROMPT.replace("{span}", "one inning" if span == 1 else f"{span} consecutive innings")
        for label in labels:
            prompt = prompt.replace("{" + label + "}", texts[key[label]].strip())
        (tdir / "prompt.txt").write_text(prompt)
        print(f"triplet {n:02d}: inning {inning}, sleep {episode}, real {Path(feed).stem}, sim {sim_seed}")


KIND = {"real": "real", "handwritten": "sleep", "simulated": "sim"}


def score(out):
    rows, all_right, per_kind = [], 0, {"real": [0, 0], "sleep": [0, 0], "sim": [0, 0]}
    for tdir in sorted(Path(out).glob("triplet_*")):
        answer_path = tdir / "answer.json"
        if not answer_path.exists():
            continue
        key = json.loads((tdir / "key.json").read_text())["key"]
        answer = json.loads(answer_path.read_text())
        right = {label: KIND.get(str(answer.get(label, "")).lower()) == kind for label, kind in key.items()}
        for label, kind in key.items():
            per_kind[kind][0] += right[label]
            per_kind[kind][1] += 1
        all_right += all(right.values())
        rows.append((tdir.name, all(right.values()), answer.get("confidence")))
    n = len(rows)
    print(f"{n} triplets judged; all three right in {all_right} (chance: {n / 6:.1f})")
    for kind, (r, t) in per_kind.items():
        if t:
            print(f"  {kind:5} identified {r}/{t}")
    for name, ok, conf in rows:
        print(f"  {name}: {'right' if ok else 'wrong'} (confidence {conf})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", required=True)
    b.add_argument("--count", type=int, default=12)
    b.add_argument("--real-feeds", required=True, help="glob of StatsAPI live-feed JSON files")
    b.add_argument("--seed", type=int, default=None)
    b.add_argument("--innings", type=int, default=1, help="innings per excerpt")
    s = sub.add_parser("score")
    s.add_argument("--out", required=True)
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.out, args.count, args.real_feeds, args.seed, args.innings)
    else:
        score(args.out)


if __name__ == "__main__":
    main()
