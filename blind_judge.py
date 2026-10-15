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

from anonymize_real_gameday import (
    anonymize_gameday_data, assign_player_names, collect_players, player_sides, validate_player_names,
)
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
    return add_designated_hitter(json.loads((FIXTURE_DIR / f"episode_{episode}.json").read_text()))


DH_IDS = {"home": 990001, "away": 990002}


def add_designated_hitter(data):
    """Sleep Baseball games have the pitcher bat; the sim and every real 2026
    game use the DH, so "that will bring up the pitcher" named the hand-written
    excerpt on its own. Put a designated hitter in the pitcher's lineup spot:
    every play is unchanged, only who is batting (or running) for him."""
    data = copy.deepcopy(data)
    pitchers = {play["matchup"]["pitcher"]["id"] for play in data["liveData"]["plays"]["allPlays"]}
    # Which side each pitcher id batted for (a real feed can also map a hitter
    # and a pitcher onto one of our ids, so don't assume it's his own side).
    bats_for = {}
    for play in data["liveData"]["plays"]["allPlays"]:
        pid = play["matchup"]["batter"]["id"]
        if pid in pitchers:
            bats_for.setdefault(pid, set()).add("away" if play["about"]["isTopInning"] else "home")

    def swap(node, pid, dh):
        if isinstance(node, dict):
            if node.get("id") == pid:
                node["id"] = dh
                if "fullName" in node:
                    node["fullName"] = f"Designated Hitter {dh}"
                node.pop("link", None)
            for v in node.values():
                swap(v, pid, dh)
        elif isinstance(node, list):
            for v in node:
                swap(v, pid, dh)

    used = set()
    dh_hands = {}
    for play in data["liveData"]["plays"]["allPlays"]:
        batting = "away" if play["about"]["isTopInning"] else "home"
        for pid in pitchers:
            if batting in bats_for.get(pid, ()):
                before = json.dumps(play)
                pitcher_ref = play["matchup"]["pitcher"]
                swap({k: v for k, v in play.items() if k != "matchup"}, pid, DH_IDS[batting])
                swap(play["matchup"]["batter"], pid, DH_IDS[batting])
                if play['matchup']['batter']['id'] == DH_IDS[batting]:
                    original = data['gameData']['players'].get(f'ID{pid}', {})
                    dh_hands[batting] = original.get('batSide') or play['matchup'].get('batSide')
                play["matchup"]["pitcher"] = pitcher_ref
                if json.dumps(play) != before:
                    used.add(batting)
    for side in used:
        dh = DH_IDS[side]
        data["gameData"]["players"][f"ID{dh}"] = {
            "id": dh, "fullName": f"Designated Hitter {dh}", "lastName": "Hitter",
            "primaryPosition": {"code": "D", "name": "Designated Hitter", "abbreviation": "DH"},
            "batSide": dh_hands.get(side) or {"code": "R", "description": "Right"},
            "pitchHand": {"code": "R", "description": "Right"}}
    return data


def real_game(path, seed):
    data = anonymize_gameday_data(json.loads(Path(path).read_text()), TEAMS, seed=seed)
    players = {p["id"]: p for p in data["gameData"]["players"].values()}
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



def remap_names(data, template_game_data, seed=None):
    """Give every player, team and the venue our names, consistently.

    Relievers draw their names in an order seeded per game (``seed``, else the
    game's own players): the simulator's first man out of the pen varies, so
    a real or hand-written game whose first reliever was always the first
    free roster pitcher ("Colin Miller replaces Joe Gibson") stood out.
    """
    data = copy.deepcopy(data)
    players = data["gameData"]["players"]
    registered = {p['id'] for p in players.values()}
    for pid, player in collect_players(data).items():
        if pid not in registered:
            players[f'ID{pid}'] = player
    by_id = {p["id"]: p for p in players.values()}
    rng = random.Random(str(seed) if seed is not None
                        else "|".join(sorted(str(p.get("fullName")) for p in players.values())))
    id_names = assign_player_names(data, TEAMS, rng)

    # Structured references use IDs, including players found only in credits
    # or substitutions. Rewrite free text only for unambiguous source names.
    name_counts = {}
    for pid in id_names:
        name = by_id[pid].get('fullName')
        if name:
            name_counts[name] = name_counts.get(name, 0) + 1
    mapping = {by_id[pid]["fullName"]: new for pid, new in id_names.items()
               if name_counts.get(by_id[pid].get("fullName")) == 1}
    full = sorted(mapping, key=len, reverse=True)
    pattern = re.compile(r"\b(?:" + "|".join(re.escape(name) for name in full) + r")\b") if full else None

    def swap(text):
        return pattern.sub(lambda m: mapping[m[0]], text) if pattern else text

    def walk(node):
        if isinstance(node, dict):
            new = id_names.get(node.get("id"))
            if new is None and "fullName" in node:
                new = mapping.get(node["fullName"])
            if new:
                node["fullName"] = new
                parts = new.split()
                first, last = parts[0], parts[-1]
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
    validate_player_names(data, 'remapped game')
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
            "sleep": remap_names(sleep_game(episode), template, seed=f"{sim_seed}:sleep"),
            "real": remap_names(real_game(feed, seed=sim_seed), template, seed=f"{sim_seed}:real"),
            "sim": sim_game(sim_seed),
        }
        for kind, data in sources.items():
            validate_player_names(data, f'triplet {n:02d} {kind}')
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
