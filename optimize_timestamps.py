import json
import re
from renderers.narrative.renderer import NarrativeRenderer
from datetime import datetime

with open('pbp_example_3.txt', 'r') as f:
    target_text = f.read()
target_words = set(re.findall(r'\b\w+\b', target_text.lower()))

with open('pbp_example_3_draft.json', 'r') as f:
    data = json.load(f)

# Direct mode reads fractional seconds.
# `index = int(digits_str)`
# We want to iterate through plays/events and find the best index for each `startTime` and `endTime`.
# To do this correctly, we could just evaluate the score incrementally, but the easiest is to just
# brute force the fraction for each event to maximize local match, or just do a simple greedy search.

def format_time(t_str, index):
    # index is integer, we'll zero-pad it to 6 digits
    base = t_str.split('+')[0]
    if '.' in base:
        base = base.split('.')[0]
    return f"{base}.{index:06d}+00:00"

def get_score(gameday_data):
    renderer = NarrativeRenderer(gameday_data, seed=0)
    rendered = renderer.render()
    rendered_words = set(re.findall(r'\b\w+\b', rendered.lower()))
    intersection = target_words.intersection(rendered_words)
    union = target_words.union(rendered_words)
    jaccard = len(intersection) / len(union) if union else 0
    return jaccard

# Let's brute force `gameData.datetime.dateTime`
best_jaccard = get_score(data)
for play_idx, play in enumerate(data['liveData']['plays']['allPlays']):
    print(f"Optimizing play {play_idx} / {len(data['liveData']['plays']['allPlays'])}")

    # optimize play about startTime
    best_idx = 0
    current_time = play['about']['startTime']
    for i in range(100):
        play['about']['startTime'] = format_time(current_time, i)
        score = get_score(data)
        if score > best_jaccard:
            best_jaccard = score
            best_idx = i
    play['about']['startTime'] = format_time(current_time, best_idx)

    # optimize events startTime
    for ev_idx, ev in enumerate(play['playEvents']):
        if 'startTime' in ev:
            best_idx = 0
            current_time = ev['startTime']
            for i in range(100):
                ev['startTime'] = format_time(current_time, i)
                score = get_score(data)
                if score > best_jaccard:
                    best_jaccard = score
                    best_idx = i
            ev['startTime'] = format_time(current_time, best_idx)

    # optimize play about endTime
    if 'endTime' in play['about']:
        best_idx = 0
        current_time = play['about']['endTime']
        for i in range(100):
            play['about']['endTime'] = format_time(current_time, i)
            score = get_score(data)
            if score > best_jaccard:
                best_jaccard = score
                best_idx = i
        play['about']['endTime'] = format_time(current_time, best_idx)

print(f"Best Jaccard: {best_jaccard}")

with open('pbp_example_3_draft.json', 'w') as f:
    json.dump(data, f, indent=2)
