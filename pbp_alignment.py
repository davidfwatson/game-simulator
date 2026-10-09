"""Shared coverage metrics for source and rendered play-by-play transcripts."""

from dataclasses import dataclass
import re


def content_text(text):
    """Remove playback timing markers before measuring broadcast language."""
    return '\n'.join(
        line for line in text.splitlines()
        if not line.strip().startswith('[TTS SPLIT')
    )


def get_words(text):
    return re.findall(r'\b\w+\b', text.lower())


def get_ngrams(text, n=5):
    words = get_words(text)
    return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))


def normalize_line(line):
    """Normalize capitalization, count formats and trivial punctuation."""
    s = line.strip().lower()
    count_words = ('oh', 'one', 'two', 'three')
    for w1 in count_words:
        for w2 in count_words:
            s = s.replace(f'{w1} and {w2}', f'{w1}-{w2}')
    s = re.sub(r'[.,]\s+(\w+-\w+)', r', \1', s)
    s = s.replace('called a strike', 'called strike')
    s = re.sub(r'\.\s+([a-z])', r', \1', s)
    return s


def _line_similarity(a, b):
    """Word-level Jaccard between two normalized lines."""
    wa = set(get_words(normalize_line(a)))
    wb = set(get_words(normalize_line(b)))
    if not wa and not wb:
        return 1.0
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def positional_line_match(target_text, rendered_text, wiggle_pct=0.08, wiggle_min=5):
    """Match each source line near its proportional position in the output.

    Returns (exact, near90, near75, n_target). Exact matches require the
    normalized strings to be equal; shared vocabulary counts as fuzzy.
    """
    target_lines = [line for line in target_text.split('\n') if line.strip()]
    rendered_lines = [line for line in rendered_text.split('\n') if line.strip()]
    target_norm = [normalize_line(line) for line in target_lines]
    rendered_norm = [normalize_line(line) for line in rendered_lines]
    n_target = len(target_lines)
    n_rendered = len(rendered_lines)
    exact = near90 = near75 = 0
    used = set()

    for ti, tline in enumerate(target_lines):
        prop = ti / n_target if n_target else 0
        center = int(prop * n_rendered)
        wiggle = max(wiggle_min, int(wiggle_pct * n_rendered))
        lo = max(0, center - wiggle)
        hi = min(n_rendered, center + wiggle + 1)
        best_sim = 0.0
        best_ri = -1
        best_exact = False
        tn = target_norm[ti]
        for ri in range(lo, hi):
            if ri in used:
                continue
            if rendered_norm[ri] == tn:
                best_sim = 1.0
                best_ri = ri
                best_exact = True
                break
            sim = _line_similarity(tline, rendered_lines[ri])
            if sim > best_sim:
                best_sim = sim
                best_ri = ri

        if best_exact:
            exact += 1
            used.add(best_ri)
        elif best_sim >= 0.9:
            near90 += 1
            used.add(best_ri)
        elif best_sim >= 0.75:
            near75 += 1
            used.add(best_ri)

    return exact, near90, near75, n_target


def positional_line_match_content(target_text, rendered_text, wiggle_pct=0.08, wiggle_min=5):
    return positional_line_match(
        content_text(target_text), content_text(rendered_text), wiggle_pct, wiggle_min
    )


@dataclass(frozen=True)
class AlignmentMetrics:
    word_jaccard: float
    ngram_coverage: float
    exact: int
    near90: int
    near75: int
    target_lines: int

    @property
    def exact_fraction(self):
        return self.exact / self.target_lines if self.target_lines else 0.0


def alignment_metrics(target_text, rendered_text, *, content_only=True):
    """Measure vocabulary, source five-gram recall and positional line matches.

    Timing markers are excluded by default. Five-grams span content lines,
    so playback boundaries cannot add shared words or alter phrase coverage.
    """
    if content_only:
        target_text = content_text(target_text)
        rendered_text = content_text(rendered_text)
    target_words = set(get_words(target_text))
    rendered_words = set(get_words(rendered_text))
    union = target_words | rendered_words
    jaccard = len(target_words & rendered_words) / len(union) if union else 0.0
    target_ngrams = get_ngrams(target_text)
    rendered_ngrams = get_ngrams(rendered_text)
    ngram_coverage = (
        len(target_ngrams & rendered_ngrams) / len(target_ngrams)
        if target_ngrams else 0.0
    )
    return AlignmentMetrics(
        jaccard, ngram_coverage, *positional_line_match(target_text, rendered_text)
    )
