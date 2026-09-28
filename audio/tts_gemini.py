#!/usr/bin/env python3
"""Gemini 3.8 Flash TTS for the play-by-play announcer.

Standard library only, so it runs anywhere GEMINI_API_KEY is set (including
the Linode, where podcast-maker's .env already holds the key).

    python tts_gemini.py segments.json outdir [--env path/to/.env]

segments.json is a list of {"id": ..., "text": ...}. Each segment is written to
outdir/<id>.wav (24 kHz mono 16-bit). Segments whose file already exists are
skipped, so an interrupted run resumes.
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

MODEL = "gemini-3.8-flash-tts"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"

# Every segment carries the same voice and style so the announcer sounds like
# one person across ~40 separate calls.
VOICE = "Rasalgethi"
STYLE = (
    "A warm, relaxed veteran radio baseball announcer calling a quiet late-night "
    "game. Natural, full speaking voice at normal conversational volume: not "
    "whispering, not breathy, not hushed. Easygoing, unhurried pace and a "
    "friendly, homey tone. Understated on big plays, a little more energy but "
    "never shouting. A short natural pause at each ellipsis while the pitch is "
    "on its way."
)


def load_env(path):
    """Minimal KEY=VALUE .env reader, so the Linode run needs no dotenv."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def synthesize(text, voice=VOICE, style=STYLE, retries=3):
    """Return WAV bytes for one segment."""
    body = {
        "model": MODEL,
        "input": [{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": text,
                "annotations": [{"type": "speech_metadata", "style": style}],
            }],
        }],
        "response_format": {"type": "audio"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": os.environ["GEMINI_API_KEY"],
        },
    )
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.load(resp)
            return base64.b64decode(_find_audio(data))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError) as e:
            detail = e.read().decode()[:300] if isinstance(e, urllib.error.HTTPError) else str(e)
            if attempt == retries - 1:
                raise RuntimeError(f"TTS failed for {text[:40]!r}: {detail}") from e
            time.sleep(5 * (attempt + 1))


def _find_audio(data):
    """Pull the base64 audio out of an interaction response.

    The SDK exposes it as ``output_audio``; the raw REST body nests it in an
    output content block, so search for the first audio-typed ``data`` field.
    """
    def walk(node):
        if isinstance(node, dict):
            mime = str(node.get("mime_type") or node.get("mimeType") or node.get("type") or "")
            if "data" in node and isinstance(node["data"], str) and "audio" in mime:
                return node["data"]
            children = node.values()
        elif isinstance(node, list):
            children = node
        else:
            return None
        for child in children:
            found = walk(child)
            if found:
                return found
        return None

    found = walk(data)
    if not found:
        raise KeyError(f"no audio in response: {json.dumps(data)[:300]}")
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("segments")
    ap.add_argument("outdir")
    ap.add_argument("--env")
    ap.add_argument("--voice", default=VOICE)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    if args.env:
        load_env(args.env)
    os.makedirs(args.outdir, exist_ok=True)
    with open(args.segments) as f:
        segments = json.load(f)

    def run(seg):
        path = os.path.join(args.outdir, f"{seg['id']}.wav")
        if os.path.exists(path):
            return
        wav = synthesize(seg["text"], voice=args.voice)
        with open(path + ".tmp", "wb") as f:
            f.write(wav)
        os.replace(path + ".tmp", path)
        print(f"  {seg['id']}: {seg['text'][:60]}", file=sys.stderr)

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(run, segments))


if __name__ == "__main__":
    main()
