"""Shared PBP fixture catalog and transcript comparison metrics.

Every ``pbp_example_*.txt`` reference must have a catalog entry, a Gameday
fixture, and a rendered snapshot. Register new examples here after reviewing
their pregame boundaries and establishing their own comparison minimums.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import NamedTuple

from transcript_asides import ASIDE_BREAK, break_segments


REPOSITORY_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class PBPExample:
    number: int
    target_skip: int
    rendered_skip: int = 30
    jaccard_min: float = 0.48
    ngram_min: float = 0.12
    line_exact_min: float = 0.40
    content_exact_min: float = 0.0

    @property
    def target_file(self) -> str:
        return f"pbp_example_{self.number}.txt"

    @property
    def fixture_file(self) -> str:
        return f"test_fixture_pbp_example_{self.number}.json"

    @property
    def snapshot_file(self) -> str:
        return f"test_fixture_pbp_example_{self.number}.txt"


# Reviewed word, phrase, and line minimums. Content-only minimums also guard
# against the many repeated TTS markers masking prose regressions. Annotated
# host asides (transcript_asides/) are excluded from the target, like the cut
# breaks. After the per-point refit (fit_transcript_games.py --references),
# any minimum more than four points below its measurement was raised to three
# points below it, rounded down; the batted-ball, runner, season-record and
# pinch-hitter facts (missed_words.py) raised them again the same way.
PBP_EXAMPLES = (
    PBPExample(1, target_skip=28, jaccard_min=0.66, ngram_min=0.32,
               line_exact_min=0.51, content_exact_min=0.19),
    PBPExample(2, target_skip=35, jaccard_min=0.65, ngram_min=0.38,
               line_exact_min=0.57, content_exact_min=0.22),
    PBPExample(3, target_skip=33, jaccard_min=0.68, ngram_min=0.33,
               line_exact_min=0.45, content_exact_min=0.05),
    PBPExample(4, target_skip=27, jaccard_min=0.62, ngram_min=0.30,
               line_exact_min=0.53, content_exact_min=0.14),
)

# Each transcript case must pass an ordered source-phrase comparison and exact
# snapshot replay. Preserve the reviewed per-episode coverage as pools grow.
TRANSCRIPT_CASE_MINIMUMS = {
    1: 4, 5: 5, 11: 4, 13: 4, 20: 4, 29: 4, 35: 4, 37: 4,
    39: 5, 41: 5, 45: 5, 46: 5, 49: 5, 50: 5, 51: 5, 52: 5, 53: 5,
}

# Whole-broadcast reconstructions include every observed appearance segment and
# delivered pitch. The two interrupted broadcasts retain their partial endings.
# Phrase recall and ordered words are approximate comparisons, not claims of
# verbatim recreation of announcer banter or the complete broadcast. Annotated
# host asides are excluded from the source side, like the cut breaks. After
# gates were fitted per point (fit_transcript_games.py), wording minimums more
# than four points below the measurement were raised to three points below
# it, rounded down, and again after the batted-ball, runner, season-record and
# pinch-hitter facts were recorded (missed_words.py).
FULL_TRANSCRIPT_MINIMUMS = {
    episode: dict(appearances=appearances, pitches=pitches,
                  ngram=ngram, mean_play_word_coverage=coverage)
    for episode, appearances, pitches, ngram, coverage in (
        (1, 73, 254, .13, .49), (5, 73, 270, .25, .67),
        (11, 50, 198, .21, .67), (13, 70, 295, .23, .68),
        (20, 67, 223, .26, .72), (29, 68, 217, .27, .67),
        (35, 63, 207, .30, .69), (37, 64, 220, .33, .75),
        (39, 68, 224, .36, .75), (41, 62, 199, .36, .74),
        (45, 72, 237, .33, .70), (46, 76, 254, .38, .75),
        (49, 63, 214, .40, .79), (50, 66, 170, .35, .71),
        (51, 47, 152, .31, .72), (52, 62, 200, .34, .71),
        (53, 62, 193, .37, .74),
    )
}


def validate_transcript_counts(counts, minimums=TRANSCRIPT_CASE_MINIMUMS):
    if set(counts) != set(minimums):
        raise ValueError('Transcript episodes differ from the reviewed catalog in pbp_comparison.py')
    for episode, minimum in minimums.items():
        if counts[episode] < minimum:
            raise ValueError(f'episode_{episode:03d}: {counts[episode]} cases is below the {minimum}-case minimum')


def check_transcript_examples():
    from transcript_comparison import check_catalog

    counts = check_catalog()
    validate_transcript_counts(counts)
    return counts


def discover_pbp_examples(
    root: Path = REPOSITORY_ROOT,
    examples: tuple[PBPExample, ...] = PBP_EXAMPLES,
) -> tuple[PBPExample, ...]:
    """Validate the catalog against disk so new references cannot go untested."""
    if len({example.number for example in examples}) != len(examples):
        raise ValueError("Duplicate example numbers in PBP_EXAMPLES")

    expected = {
        filename
        for example in examples
        for filename in (example.target_file, example.fixture_file, example.snapshot_file)
    }
    discovered = {
        path.name
        for pattern in (
            "pbp_example_*.txt",
            "test_fixture_pbp_example_*.json",
            "test_fixture_pbp_example_*.txt",
        )
        for path in root.glob(pattern)
        if path.is_file()
    }
    problems = []
    if unregistered := discovered - expected:
        problems.append(
            "Unregistered PBP files: " + ", ".join(sorted(unregistered))
            + ". Add their example to PBP_EXAMPLES in pbp_comparison.py with "
            "reviewed pregame offsets and comparison minimums."
        )
    if missing := expected - discovered:
        problems.append("Missing PBP files: " + ", ".join(sorted(missing)))
    if problems:
        raise ValueError("\n".join(problems))
    return examples


def render_example(example: PBPExample, root: Path = REPOSITORY_ROOT) -> str:
    """Render a fixture using the same entry point as its snapshot test."""
    from renderers.narrative.renderer import NarrativeRenderer

    data = json.loads((root / example.fixture_file).read_text(encoding="utf-8"))
    return NarrativeRenderer(data).render()


def normalize_line(line: str) -> str:
    """Ignore case, count separators, and minor broadcast punctuation."""
    normalized = line.strip().lower()
    count_words = ("oh", "one", "two", "three")
    for first in count_words:
        for second in count_words:
            normalized = normalized.replace(f"{first} and {second}", f"{first}-{second}")
    normalized = re.sub(r"[.,]\s+(\w+-\w+)", r", \1", normalized)
    normalized = normalized.replace("called a strike", "called strike")
    return re.sub(r"\.\s+([a-z])", r", \1", normalized)


def _words(text: str) -> set[str]:
    return set(re.findall(r"\b\w+\b", text.lower()))


def get_ngrams(text: str, n: int = 5) -> set[tuple[str, ...]]:
    """Five-grams within each aside-free segment; none straddles a removed aside."""
    ngrams = set()
    for segment in break_segments(text):
        words = re.findall(r"\b\w+\b", segment.lower())
        ngrams.update(tuple(words[index:index + n]) for index in range(len(words) - n + 1))
    return ngrams


def _content_lines(text: str) -> list[str]:
    """Non-blank lines, with a line split into separate pieces at each removed
    aside so an exact match cannot join words that were never adjacent."""
    lines = []
    for line in text.splitlines():
        if ASIDE_BREAK in line:
            lines.extend(piece for piece in break_segments(line) if re.search(r"\w", piece))
        elif line.strip():
            lines.append(line)
    return lines


class LineMatch(NamedTuple):
    exact: int
    near90: int
    near75: int
    total: int

    @property
    def exact_fraction(self) -> float:
        return self.exact / self.total if self.total else 0.0


def positional_line_match(
    target_text: str,
    rendered_text: str,
    wiggle_pct: float = 0.08,
    wiggle_min: int = 5,
) -> LineMatch:
    """Match lines once within a window around their proportional position.

    Exact matches require identical normalized text; Jaccard overlap alone
    cannot establish exactness because it discards word order and repetition.
    The near90 and near75 counts are exclusive of each higher match band.
    """
    target = [normalize_line(line) for line in _content_lines(target_text)]
    rendered = [normalize_line(line) for line in _content_lines(rendered_text)]
    target_words = [_words(line) for line in target]
    rendered_words = [_words(line) for line in rendered]
    used = set()
    exact = near90 = near75 = 0
    wiggle = max(wiggle_min, int(wiggle_pct * len(rendered)))

    for target_index, target_line in enumerate(target):
        center = int(target_index / len(target) * len(rendered))
        lo = max(0, center - wiggle)
        hi = min(len(rendered), center + wiggle + 1)
        best_similarity = 0.0
        best_index = -1
        is_exact = False
        for rendered_index in range(lo, hi):
            if rendered_index in used:
                continue
            if rendered[rendered_index] == target_line:
                best_index = rendered_index
                is_exact = True
                break
            target_set = target_words[target_index]
            rendered_set = rendered_words[rendered_index]
            union = target_set | rendered_set
            similarity = len(target_set & rendered_set) / len(union) if union else 0.0
            if similarity > best_similarity:
                best_similarity = similarity
                best_index = rendered_index

        if is_exact:
            exact += 1
        elif best_similarity >= 0.9:
            near90 += 1
        elif best_similarity >= 0.75:
            near75 += 1
        else:
            continue
        used.add(best_index)

    return LineMatch(exact, near90, near75, len(target))


def _without_tts(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.strip().startswith("[TTS SPLIT"))


def positional_line_match_content(
    target_text: str,
    rendered_text: str,
    wiggle_pct: float = 0.08,
    wiggle_min: int = 5,
) -> LineMatch:
    """Compare spoken content without counting repeated TTS delay markers."""
    return positional_line_match(
        _without_tts(target_text), _without_tts(rendered_text), wiggle_pct, wiggle_min
    )


@dataclass(frozen=True)
class ComparisonScores:
    jaccard: float
    ngram: float
    all_lines: LineMatch
    content_lines: LineMatch

    def failures(self, example: PBPExample) -> list[str]:
        metrics = (
            ("Word Jaccard", self.jaccard, example.jaccard_min),
            ("5-gram match", self.ngram, example.ngram_min),
            ("Exact lines (all)", self.all_lines.exact_fraction, example.line_exact_min),
            ("Exact lines (content)", self.content_lines.exact_fraction, example.content_exact_min),
        )
        return [
            f"{name}: {actual:.2%} is below {minimum:.2%}"
            for name, actual, minimum in metrics
            if actual < minimum
        ]


def compare_transcripts(target: str, rendered: str) -> ComparisonScores:
    """Compute the metrics used by both regression tests and CLI reporting."""
    target_words = _words(target)
    rendered_words = _words(rendered)
    union = target_words | rendered_words
    target_ngrams = get_ngrams(target)
    rendered_ngrams = get_ngrams(rendered)
    return ComparisonScores(
        jaccard=len(target_words & rendered_words) / len(union) if union else 0.0,
        ngram=len(target_ngrams & rendered_ngrams) / len(target_ngrams) if target_ngrams else 0.0,
        all_lines=positional_line_match(target, rendered),
        content_lines=positional_line_match_content(target, rendered),
    )


def compare_example(
    example: PBPExample,
    rendered: str,
    root: Path = REPOSITORY_ROOT,
) -> ComparisonScores:
    from transcript_asides import metric_source_text

    # Host asides count for nothing, like the breaks cut from the sources.
    target = metric_source_text(root / example.target_file, root, root / "transcript_asides")
    return compare_transcripts(
        "\n".join(target.splitlines()[example.target_skip:]),
        "\n".join(rendered.splitlines()[example.rendered_skip:]),
    )
