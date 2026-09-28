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


# Preserve the original word, phrase, and line minimums. Content-only minimums
# also guard against the many repeated TTS markers masking prose regressions.
PBP_EXAMPLES = (
    PBPExample(1, target_skip=28, content_exact_min=0.13),
    PBPExample(2, target_skip=35, content_exact_min=0.16),
    PBPExample(3, target_skip=33, content_exact_min=0.05),
    PBPExample(4, target_skip=27, content_exact_min=0.12),
)


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
    words = re.findall(r"\b\w+\b", text.lower())
    return {tuple(words[index:index + n]) for index in range(len(words) - n + 1)}


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
    target = [normalize_line(line) for line in target_text.splitlines() if line.strip()]
    rendered = [normalize_line(line) for line in rendered_text.splitlines() if line.strip()]
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
    target = (root / example.target_file).read_text(encoding="utf-8")
    return compare_transcripts(
        "\n".join(target.splitlines()[example.target_skip:]),
        "\n".join(rendered.splitlines()[example.rendered_skip:]),
    )
