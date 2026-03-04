import json

def get_words(s):
    import re
    return set(re.findall(r'\b\w+\b', s.lower()))

def get_ngrams(s, n=5):
    import re
    words = re.findall(r'\b\w+\b', s.lower())
    return set(tuple(words[i:i+n]) for i in range(len(words)-n+1))

with open('pbp_example_3.txt', 'r') as f:
    text = f.read()

with open('pbp_example_3_draft.json', 'r') as f:
    data = json.load(f)

from renderers.narrative.renderer import NarrativeRenderer
renderer = NarrativeRenderer(data)
rendered = renderer.render()

text_words = get_words(text)
rendered_words = get_words(rendered)

intersection = text_words.intersection(rendered_words)
union = text_words.union(rendered_words)
jaccard = len(intersection) / len(union) if union else 0

text_ngrams = get_ngrams(text)
rendered_ngrams = get_ngrams(rendered)

intersection_ngrams = text_ngrams.intersection(rendered_ngrams)
ngram_percentage = len(intersection_ngrams) / len(text_ngrams) if text_ngrams else 0

print(f"Jaccard: {jaccard*100:.2f}%")
print(f"5-gram match: {ngram_percentage*100:.2f}%")
