#!/usr/bin/env python3
"""Assemble one inning of a simulated game into broadcast audio.

    python audio/assemble_inning.py --game 1 --inning 1 --out inning.mp3

Pipeline:
  1. Render the example game's narrative play-by-play.
  2. Cut out one full inning (top and bottom), dropping the pregame lineups
     and the commercial break between halves.
  3. Voice each [TTS SPLIT] chunk with Gemini TTS (audio/tts_gemini.py). Runs
     locally when GEMINI_API_KEY is set, or on a remote host over ssh with
     --tts-remote (the key never leaves that host).
  4. Lay the voice lines out on a timeline, honouring the DELAY values as the
     silence between lines, and drop a mitt pop or bat crack into the
     announcer's "..." pause on every pitch, plus crowd reactions.
  5. Mix over a looped ballpark crowd bed with ffmpeg.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

AUDIO_DIR = Path(__file__).resolve().parent
SFX_DIR = AUDIO_DIR / "sfx"
DEFAULT_CACHE = AUDIO_DIR / "cache"
SAMPLE_RATE = 48000

SPLIT_RE = re.compile(r"^\[TTS SPLIT HERE DELAY:([\d.]+)s\]$")
HALF_BREAK_DELAY = 15.0
# The renderer's 15s half-inning break assumes a commercial fills it; with the
# commercial gone, the crowd alone carries a shorter gap.
BREAK_PAUSE = 8.0
LEAD_IN = 4.0
TAIL = 6.0


# --------------------------------------------------------------------------
# Script extraction
# --------------------------------------------------------------------------

@dataclass
class Segment:
    text: str
    pause: float  # silence before this line, seconds
    half: str  # "top" or "bottom"
    cues: list = field(default_factory=list)

    @property
    def id(self):
        return hashlib.sha1(self.text.encode()).hexdigest()[:16]


def render_game(game_index):
    from example_games import EXAMPLE_GAMES
    return EXAMPLE_GAMES[game_index - 1].render("narrative")


def extract_inning(text, inning):
    """Return the Segments for one full inning of rendered narrative text."""
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if "we are underway" in l)
    venue_match = re.search(r"\bfrom (.+?) in [A-Z]", text) or re.search(r"underway here at (.+?)\.", text)
    venue = venue_match.group(1) if venue_match else None

    # Half innings are separated by the renderer's hardcoded 15s break marker.
    halves, current = [], []
    for line in lines[start:]:
        m = SPLIT_RE.match(line.strip())
        if m and float(m.group(1)) == HALF_BREAK_DELAY:
            halves.append(current)
            current = []
        else:
            current.append(line)
    halves.append(current)

    segments = []
    for half_index, half in ((2 * inning - 2, "top"), (2 * inning - 1, "bottom")):
        pause = BREAK_PAUSE if segments else LEAD_IN
        buf = []

        def flush():
            nonlocal pause
            spoken = clean_line(" ".join(buf), half, inning, venue)
            if spoken:
                segments.append(Segment(spoken, pause, half))
            buf.clear()

        for line in halves[half_index]:
            m = SPLIT_RE.match(line.strip())
            if m:
                flush()
                pause = float(m.group(1))
            elif line.strip():
                buf.append(line.strip())
            elif buf:
                # A blank line closes a paragraph (e.g. the half-inning wrap).
                flush()
                pause = 2.5
        flush()
    return segments


WELCOME_BACK_RE = re.compile(r"^(And )?(welcome back|we're back)\b", re.I)
WE_LL_BE_BACK_RE = re.compile(r"\s*(And )?[Ww]e'll be back\b[^.]*\.")


def clean_line(text, half, inning, venue):
    """Strip commercial-break phrasing that makes no sense without the break."""
    text = WE_LL_BE_BACK_RE.sub("", text).strip()
    if WELCOME_BACK_RE.match(text):
        ordinal = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
                   6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth"}.get(inning, f"{inning}th")
        first_sentence_end = text.find(". ")
        rest = text[first_sentence_end + 2:] if first_sentence_end >= 0 else ""
        where = f" here at {venue}" if venue else ""
        text = f"{half.capitalize()} of the {ordinal}{where}. {rest}".strip()
    return text


# --------------------------------------------------------------------------
# Sound cues
# --------------------------------------------------------------------------

FOUL_WORDS = ("foul", "fouls", "fouled", "tipped", "tips")
IN_PLAY_WORDS = (
    "grounded", "ground ball", "grounder", "lined", "liner", "line drive", "lifted",
    "fly ball", "flied", "popped", "pop up", "chopped", "bounced", "bouncer",
    "bunt", "roller", "blooper", "flare", "drive", "drilled", "smoked", "hammered",
    "hit in the air", "into left", "into right", "into center", "up the middle",
    "base hit", "single", "double", "triple", "home run", "gone", "swung on and hit",
    "chopper", "comebacker", "hopper", "one hopper", "dribbler", "tapper", "grounder",
    "sharply", "in the air", "high fly", "bloop", "slapped", "rolled",
)
NO_CONTACT_SOUND = ("hit by", "plunk", "hits him", "wears it", "in the dirt")
HIT_WORDS = ("single", "double", "triple", "drops in", "base hit", "base knock")
HOMER_WORDS = ("home run", "gone", "out of here", "homer")
STRIKEOUT_WORDS = ("strikes out", "rings him up", "fans him", "strike three", "goes down swinging",
                   "gets him swinging", "goes down looking", "goes down for out",
                   "struck out", "punch out", "caught looking")
INNING_OVER_WORDS = ("end the inning", "to end the", "retire the side", "side retired")
RUN_WORDS = ("scores", "comes home", "comes in to score", "run scores", "runs score")


STEAL_RE = re.compile(r"(there he goes|the runner breaks|runner goes|and he's going)!", re.I)


def classify(segment):
    """Attach sound cues to a segment based on what the announcer says.

    Each cue is (kind, char_index, offset): the sound lands in the pause the
    TTS leaves nearest that character position (normally the "..." where the
    pitch is on its way), plus offset seconds.
    """
    text = segment.text
    if "..." not in text:
        return []
    ellipsis = text.index("...")
    cues = []

    def has(words, span):
        return any(re.search(rf"\b{re.escape(w)}\b", span.lower()) for w in words)

    def contact(span):
        if has(NO_CONTACT_SOUND, span):
            return None
        if has(FOUL_WORDS, span) and not has(HIT_WORDS, span):
            return "foul"
        if has(IN_PLAY_WORDS, span):
            return "bat"
        return "mitt"

    steal = STEAL_RE.search(text)
    if steal and steal.end() < ellipsis:
        # "Here's the one-oh pitch and the runner breaks! Slider downstairs.
        # The throw down... not in time!" -- a mitt pop anywhere in here lands next to
        # "there he goes" or the throw and reads as the wrong event, so a
        # steal line carries no contact sound.
        pitch_at = steal.end()
    else:
        pitch_at = ellipsis
        kind = contact(text[ellipsis:])
        if kind:
            cues.append((kind, pitch_at, 0.0))

    after = text[pitch_at:]
    home_batting = segment.half == "bottom"
    if has(HOMER_WORDS, after):
        cues.append(("roar" if home_batting else "groan", pitch_at, 0.35))
    elif has(HIT_WORDS, after) or has(RUN_WORDS, after):
        cues.append(("cheer" if home_batting else "groan", pitch_at, 0.35))
    elif not home_batting and (has(STRIKEOUT_WORDS, after) or has(INNING_OVER_WORDS, after)):
        cues.append(("applause", pitch_at, 0.35))
    return cues


# Sound library: kind -> [(file, gain dB)], cycled in order. Files live in
# audio/sfx/ (credits in SOURCES.md): point sounds are peak-normalised to
# -3 dBFS and crowd clips to -23 LUFS, so gains are relative to those. The
# announcer is normalised to -19 LUFS.
SFX = {
    "mitt": [("mitt_1.mp3", -12), ("mitt_2.mp3", -12), ("mitt_3.mp3", -12), ("mitt_4.mp3", -12)],
    "bat": [("bat_1.mp3", -9), ("bat_3.mp3", -9), ("bat_2.mp3", -9), ("bat_4.mp3", -9)],
    "foul": [("bat_2.mp3", -15), ("bat_4.mp3", -15), ("bat_3.mp3", -15)],
    "cheer": [("cheer_1.mp3", -6), ("cheer_2.mp3", -6)],
    "roar": [("cheer_big.mp3", -8)],
    "applause": [("applause_1.mp3", -8), ("applause_3.mp3", -8), ("applause_2.mp3", -8)],
    "groan": [("groan_1.mp3", -9), ("groan_2.mp3", -9)],
}
# Two crowd loops of different lengths, layered, so the repeat point drifts
# and never lines up; low-passed so the crowd sits far behind the booth.
BEDS = [("bed_1.mp3", -9), ("bed_2.mp3", -12)]
# Contact sounds are close-miked studio recordings; a short slapback and a
# gentle top cut put them out on the field instead of in the booth.
POINT_KINDS = {"mitt", "bat", "foul"}
FIELD_FX = "aecho=0.8:0.4:35|85:0.22|0.12,lowpass=f=7000"
BED_LOWPASS_HZ = 5000


# --------------------------------------------------------------------------
# TTS
# --------------------------------------------------------------------------

def run_tts(segments, tts_dir, remote=None, remote_env=None, voice=None):
    tts_dir.mkdir(parents=True, exist_ok=True)
    todo = [s for s in segments if not (tts_dir / f"{s.id}.wav").exists()]
    if not todo:
        return
    payload = [{"id": s.id, "text": s.text} for s in todo]
    voice_args = ["--voice", voice] if voice else []
    with tempfile.TemporaryDirectory() as tmp:
        seg_file = Path(tmp) / "segments.json"
        seg_file.write_text(json.dumps(payload, indent=1))
        script = AUDIO_DIR / "tts_gemini.py"
        if remote:
            rdir = f"/tmp/gsim-tts-{os.getpid()}"
            subprocess.run(["ssh", remote, f"mkdir -p {rdir}/out"], check=True)
            subprocess.run(["scp", "-q", str(script), str(seg_file), f"{remote}:{rdir}/"], check=True)
            env_arg = f"--env {remote_env}" if remote_env else ""
            subprocess.run(["ssh", remote, f"cd {rdir} && python3 tts_gemini.py segments.json out {env_arg} {' '.join(voice_args)}"], check=True)
            subprocess.run(["scp", "-q", f"{remote}:{rdir}/out/*.wav", str(tts_dir)], check=True)
            subprocess.run(["ssh", remote, f"rm -rf {rdir}"], check=True)
        else:
            subprocess.run([sys.executable, str(script), str(seg_file), str(tts_dir), *voice_args], check=True)


# --------------------------------------------------------------------------
# Timing helpers
# --------------------------------------------------------------------------

def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True).stdout
    return float(out)


def silences(path, noise_db=-40, min_dur=0.25):
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af",
         f"silencedetect=n={noise_db}dB:d={min_dur}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", out)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", out)]
    return list(zip(starts, ends))


def pause_time(segment, wav, char_index):
    """Time of the TTS pause nearest a character position (e.g. a "...")."""
    total = duration(wav)
    frac = char_index / max(len(segment.text), 1)
    expected = total * frac
    gaps = [(s, e) for s, e in silences(wav) if e - s >= 0.3 and s > 0.3]
    if not gaps:
        return expected
    s, e = min(gaps, key=lambda g: abs(g[0] - expected))
    return s + min(0.45, (e - s) * 0.4)


# --------------------------------------------------------------------------
# Mixing
# --------------------------------------------------------------------------

def build_timeline(segments, tts_dir):
    """Place every voice line and cue on an absolute timeline (seconds)."""
    voice, cues = [], []
    counters = {}
    t = 0.0
    for seg in segments:
        wav = tts_dir / f"{seg.id}.wav"
        t += seg.pause
        dur = duration(wav)
        voice.append((t, wav))
        for kind, char_index, offset in seg.cues:
            options = SFX[kind]
            n = counters.get(kind, 0)
            counters[kind] = n + 1
            fname, gain = options[n % len(options)]
            at = t + pause_time(seg, wav, char_index) + offset
            cues.append((at, SFX_DIR / fname, gain, FIELD_FX if kind in POINT_KINDS else None))
        t += dur
    return voice, cues, t + TAIL


def mix(voice, cues, total, out_path, beds=BEDS):
    """Mix voice + cues + looping crowd bed into one file with ffmpeg."""
    inputs, filters = [], []

    def add_input(path):
        inputs.extend(["-i", str(path)])
        return len(inputs) // 2 - 1

    # Voice track: each line delayed to its slot, then summed.
    vlabels = []
    for n, (t, wav) in enumerate(voice):
        i = add_input(wav)
        filters.append(f"[{i}:a]aresample={SAMPLE_RATE},aformat=channel_layouts=mono,"
                       f"adelay={int(t * 1000)}:all=1[v{n}]")
        vlabels.append(f"[v{n}]")
    filters.append(f"{''.join(vlabels)}amix=inputs={len(vlabels)}:normalize=0:dropout_transition=0,"
                   f"loudnorm=I=-19:TP=-2:LRA=11,apad=whole_dur={total}[voice]")
    filters.append("[voice]asplit=2[voice_out][voice_sc]")

    # Crowd bed: each loop repeated to length, layered, gently ducked under
    # the announcer.
    blabels = []
    for n, (fname, gain) in enumerate(beds):
        i = add_input(SFX_DIR / fname)
        filters.append(f"[{i}:a]aresample={SAMPLE_RATE},aformat=channel_layouts=mono,"
                       f"aloop=loop=-1:size=2147483647,atrim=0:{total},volume={gain}dB[b{n}]")
        blabels.append(f"[b{n}]")
    filters.append(f"{''.join(blabels)}amix=inputs={len(blabels)}:normalize=0,lowpass=f={BED_LOWPASS_HZ},"
                   f"afade=t=in:d=3,afade=t=out:st={total - 4:.2f}:d=4[bedraw]")
    filters.append("[bedraw][voice_sc]sidechaincompress=threshold=0.05:ratio=2.5:attack=200:release=1500[bed]")

    # Cues.
    clabels = []
    for n, (t, path, gain, fx) in enumerate(cues):
        i = add_input(path)
        fx = f"{fx}," if fx else ""
        filters.append(f"[{i}:a]aresample={SAMPLE_RATE},aformat=channel_layouts=mono,{fx}"
                       f"volume={gain}dB,adelay={int(t * 1000)}:all=1[c{n}]")
        clabels.append(f"[c{n}]")
    if clabels:
        filters.append(f"{''.join(clabels)}amix=inputs={len(clabels)}:normalize=0:dropout_transition=0[cues]")
        final_inputs = "[voice_out][bed][cues]"
        count = 3
    else:
        final_inputs, count = "[voice_out][bed]", 2
    filters.append(f"{final_inputs}amix=inputs={count}:normalize=0:duration=first,"
                   f"alimiter=limit=0.89[out]")

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.write(";\n".join(filters))
        graph = f.name
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
           "-/filter_complex", graph, "-map", "[out]", "-ac", "1"]
    if str(out_path).endswith(".mp3"):
        cmd += ["-c:a", "libmp3lame", "-b:a", "160k"]
    subprocess.run(cmd + [str(out_path)], check=True)
    os.unlink(graph)


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--game", type=int, default=1, help="example game index (1-10)")
    ap.add_argument("--inning", type=int, default=1)
    ap.add_argument("--out", default="inning.mp3")
    ap.add_argument("--cache", default=str(DEFAULT_CACHE), help="TTS cache directory")
    ap.add_argument("--voice", help="Gemini prebuilt voice (default in tts_gemini.py)")
    ap.add_argument("--tts-remote", help="ssh host to run TTS on (e.g. user@host)")
    ap.add_argument("--tts-remote-env", help=".env file on the remote host holding GEMINI_API_KEY")
    ap.add_argument("--bed", action="append", metavar="FILE:GAIN_DB",
                    help="crowd bed loop (repeatable), path relative to audio/sfx/; replaces the default beds")
    ap.add_argument("--max-lines", type=int, help="only the first N lines (for quick samples)")
    ap.add_argument("--script-only", action="store_true", help="print segments and cues, no audio")
    args = ap.parse_args()

    segments = extract_inning(render_game(args.game), args.inning)
    if args.max_lines:
        segments = segments[:args.max_lines]
    for seg in segments:
        seg.cues = classify(seg)
    beds = BEDS
    if args.bed:
        beds = [(f.rsplit(":", 1)[0], float(f.rsplit(":", 1)[1])) for f in args.bed]

    if args.script_only:
        for seg in segments:
            cues = ", ".join(k for k, _, _ in seg.cues)
            print(f"[{seg.half} +{seg.pause:>4.1f}s] {seg.text}" + (f"   <{cues}>" if cues else ""))
        return

    import tts_gemini
    voice_name = args.voice or tts_gemini.VOICE
    style_key = hashlib.sha1(tts_gemini.STYLE.encode()).hexdigest()[:8]
    tts_dir = Path(args.cache) / f"{voice_name}-{style_key}"
    run_tts(segments, tts_dir, args.tts_remote, args.tts_remote_env, args.voice)
    voice, cues, total = build_timeline(segments, tts_dir)
    mix(voice, cues, total, args.out, beds)
    print(f"Wrote {args.out} ({total / 60:.1f} min, {len(voice)} lines, {len(cues)} cues)")


if __name__ == "__main__":
    main()
