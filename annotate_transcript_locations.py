"""Annotate explicit verbal pitch locations without inventing measured zones.

Run this authoring helper after reviewing event ledgers. It retains manually
assigned locations and skips source lines containing multiple delivered pitches.
The canonical fixture compiler copies these facts; the renderer never reads
source text. Handedness and numeric tracking coordinates are not inferred.
"""
import json
import re
from collections import Counter
from transcript_game_fixtures import LEDGER_DIR, SOURCE_DIR


def location_from_words(text, code):
    text = text.casefold()
    if code not in ('B', 'C'):
        return None
    inside = bool(re.search(r'\binside\b|\btight\b|\b(?:up|down|low|high) and in\b|brushes him back', text))
    outside = bool(re.search(r'\boutside\b|\bwide\b|\b(?:up|down|low|high) and away\b', text))
    high = bool(re.search(r'\bhigh\b|\bupstairs\b|\bup and (?:in|away)\b', text))
    low = bool(re.search(r'\blow\b|\bdownstairs\b|\bat the knees\b|\bdown and (?:in|away)\b', text))
    dirt = bool(re.search(r'\bin the dirt\b|bounces? in front of (?:the|home) plate', text))
    corner = bool(re.search(r'\bcorner\b|\bthe black\b|\bthe edge\b', text))
    if code == 'C':
        if corner:
            return 'outside_corner' if outside else 'inside_corner' if inside else 'corner'
        if re.search(r'\b(?:middle|main street)\b', text):
            return 'middle'
        if low or dirt:
            return 'low'
        return None
    if inside and outside or high and low:
        return None  # Contrasting locations on one line require manual review.
    if dirt:
        return 'dirt'
    if high or low:
        vertical = 'high' if high else 'low'
        if inside or outside:
            return vertical + ('_inside' if inside else '_outside')
        return vertical
    if inside or outside:
        return 'inside' if inside else 'outside'
    return None


def main():
    for path in sorted(LEDGER_DIR.glob('episode_*.json')):
        ledger = json.loads(path.read_text())
        source = (SOURCE_DIR / ledger['source_file']).read_text().splitlines()
        pitches = [pitch for play in ledger['plays'] for pitch in play['pitches']]
        counts = Counter(pitch['line'] for pitch in pitches if pitch['code'] != 'A')
        changed = 0
        for pitch in pitches:
            if 'location' in pitch or counts[pitch['line']] != 1:
                continue
            location = location_from_words(source[pitch['line'] - 1], pitch['code'])
            if location:
                pitch['location'] = location
                changed += 1
        if changed:
            path.write_text(json.dumps(ledger, indent=2) + '\n')
        print(f'{path.stem}: {changed} explicit verbal pitch locations')


if __name__ == '__main__':
    main()
