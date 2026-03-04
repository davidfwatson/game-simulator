import json
import re
from renderers.narrative.renderer import NarrativeRenderer
from datetime import datetime

with open('pbp_example_3.txt', 'r') as f:
    target_text = f.read()

def get_ngrams(s, n=5):
    words = re.findall(r'\b\w+\b', s.lower())
    return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))

target_ngrams = get_ngrams(target_text)

with open('pbp_example_3_draft.json', 'r') as f:
    data = json.load(f)

def format_time(t_str, index):
    base = t_str.split('+')[0]
    if '.' in base:
        base = base.split('.')[0]
    return f"{base}.{index:06d}+00:00"

def get_score(gameday_data):
    renderer = NarrativeRenderer(gameday_data, seed=0)
    rendered = renderer.render()
    rendered_ngrams = get_ngrams(rendered)
    intersection_ngrams = target_ngrams.intersection(rendered_ngrams)
    return len(intersection_ngrams) / len(target_ngrams) if target_ngrams else 0

# Just try to randomly sample some timestamps and keep the best
import random
best_score = get_score(data)
for _ in range(50):
    play_idx = random.randint(0, len(data['liveData']['plays']['allPlays']) - 1)
    play = data['liveData']['plays']['allPlays'][play_idx]

    # randomly pick start, end, or an event
    choice = random.randint(0, 2)
    if choice == 0:
        old = play['about']['startTime']
        for i in range(20):
            play['about']['startTime'] = format_time(old, random.randint(0, 999999))
            score = get_score(data)
            if score > best_score:
                best_score = score
                old = play['about']['startTime']
        play['about']['startTime'] = old
    elif choice == 1 and 'endTime' in play['about']:
        old = play['about']['endTime']
        for i in range(20):
            play['about']['endTime'] = format_time(old, random.randint(0, 999999))
            score = get_score(data)
            if score > best_score:
                best_score = score
                old = play['about']['endTime']
        play['about']['endTime'] = old
    else:
        if play['playEvents']:
            ev = random.choice(play['playEvents'])
            if 'startTime' in ev:
                old = ev['startTime']
                for i in range(20):
                    ev['startTime'] = format_time(old, random.randint(0, 999999))
                    score = get_score(data)
                    if score > best_score:
                        best_score = score
                        old = ev['startTime']
                ev['startTime'] = old

print(f"Best n-gram score: {best_score}")

with open('pbp_example_3_draft.json', 'w') as f:
    json.dump(data, f, indent=2)
