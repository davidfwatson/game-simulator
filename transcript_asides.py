"""Host asides in the Sleep Baseball sources, excluded from alignment metrics.

Between-innings breaks (promos, in-character spots) were cut from the cleaned
transcripts, so they are absent from every metric's source side. Asides are
the in-call equivalent: anecdotes, banter with producer Phil, mound-visit
chatter, player trivia, in-call sponsor reads and similar talk that no
Gameday-driven engine could narrate. They stay in the source texts, which are
preserved verbatim, and are marked instead in ``transcript_asides/<stem>.json``.

Each annotation file records the source path and SHA-256 so an edited source
cannot silently shift a span. An aside entry names a one-based ``line`` and
either ``text`` (an exact substring of that line; ``occurrence`` picks among
repeats) or no text (the whole line, through ``end_line`` when given)::

    {"line": 212, "text": "there appears to be a goat in center field.",
     "category": "story", "note": "goat delay"}
    {"line": 300, "end_line": 303, "category": "banter"}

``strip_asides`` replaces those spans with ``ASIDE_BREAK`` while keeping the
line count, so source line references (ledger ranges, component provenance)
stay valid. Metrics treat the marker as a hard boundary, so the words on either
side of an aside never form a sequence that was not in the broadcast.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
ASIDE_DIR = ROOT / 'transcript_asides'
CATEGORIES = {
    'story': 'Anecdote or off-field event: goat on the field, skydiver, hot dog cannon, mascot race.',
    'incident': 'On-field interruption beyond the play record: scuffle, injury delay, rain delay talk.',
    'mound_visit': 'Chatter about what is said or meant at a mound visit (the bare visit is narratable).',
    'trivia': "Player or team history, records, nicknames, off-season life, beyond this game's facts.",
    'banter': 'Conversation with producer Phil, listener greetings, jokes, self-reference.',
    'promo': 'In-call sponsor reads, gift shop or website plugs, and other show promotion.',
    'crowd': 'Crowd, ballpark or scenery colour that is not a game fact.',
}
WORD = re.compile(r'\w')
# Stands in for a removed aside. It never occurs in a source and is not a word.
ASIDE_BREAK = '\u2016'


@dataclass(frozen=True)
class AsideSpan:
    line: int        # one-based source line
    start: int       # character offsets within that line
    end: int
    category: str
    entry: int = 0   # index of the annotation entry that produced the span

    def words(self, lines):
        return re.findall(r'\w+', lines[self.line - 1][self.start:self.end])


def annotation_path(source_path, aside_dir=ASIDE_DIR):
    return Path(aside_dir) / f'{Path(source_path).stem}.json'


def _relative(path, root):
    path = Path(path).resolve()
    try:
        return path.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return path.name


def parse_asides(annotation, source_text, source_name=None):
    """Validate an annotation against its source text and return its spans."""
    label = source_name or annotation.get('source_file', '<source>')
    digest = hashlib.sha256(source_text.encode('utf-8')).hexdigest()
    if source_name is not None and annotation.get('source_file') != source_name:
        raise ValueError(f'{label}: annotation names {annotation.get("source_file")!r}')
    if annotation.get('source_sha256') != digest:
        raise ValueError(f'{label}: source SHA-256 changed; re-review its aside spans')
    lines = source_text.splitlines()
    spans = []
    for index, entry in enumerate(annotation.get('asides', [])):
        where = f'{label} aside {index}'
        unknown = set(entry) - {'line', 'end_line', 'text', 'occurrence', 'category', 'note'}
        if unknown:
            raise ValueError(f'{where}: unknown fields {sorted(unknown)}')
        if entry.get('category') not in CATEGORIES:
            raise ValueError(f'{where}: category {entry.get("category")!r} is not one of {sorted(CATEGORIES)}')
        line = entry.get('line')
        end_line = entry.get('end_line', line)
        if type(line) is not int or type(end_line) is not int or not 1 <= line <= end_line <= len(lines):
            raise ValueError(f'{where}: line range {line}-{end_line} is outside the source')
        if 'text' in entry:
            text, occurrence = entry['text'], entry.get('occurrence', 1)
            if end_line != line:
                raise ValueError(f'{where}: a substring aside must stay within one line')
            if not isinstance(text, str) or not WORD.search(text):
                raise ValueError(f'{where}: text must contain words')
            source_line = lines[line - 1]
            positions = [m.start() for m in re.finditer(re.escape(text), source_line)]
            if not positions:
                raise ValueError(f'{where}: text is not an exact substring of line {line}')
            if 'occurrence' not in entry and len(positions) > 1:
                raise ValueError(f'{where}: text occurs {len(positions)} times on line {line}; set occurrence')
            if type(occurrence) is not int or not 1 <= occurrence <= len(positions):
                raise ValueError(f'{where}: occurrence {occurrence!r} is out of range')
            start = positions[occurrence - 1]
            spans.append(AsideSpan(line, start, start + len(text), entry['category'], index))
        else:
            if 'occurrence' in entry:
                raise ValueError(f'{where}: occurrence requires text')
            for number in range(line, end_line + 1):
                if not WORD.search(lines[number - 1]):
                    raise ValueError(f'{where}: whole-line aside covers blank line {number}')
                spans.append(AsideSpan(number, 0, len(lines[number - 1]), entry['category'], index))
    ordered = sorted(spans, key=lambda span: (span.line, span.start))
    for previous, current in zip(ordered, ordered[1:]):
        if previous.line == current.line and current.start < previous.end:
            raise ValueError(f'{label}: overlapping asides on line {current.line}')
    return ordered


def load_asides(source_path, root=ROOT, aside_dir=None, allow_missing=False):
    """Validated spans for a source file.

    Every corpus source has an annotation file, even one with no asides, so a
    missing file is an error: silently scoring the unfiltered source would hide
    a deleted or misnamed annotation. Only ad-hoc targets outside the corpus
    (``pbp_tools.py diff`` on an arbitrary file) opt in with ``allow_missing``.
    """
    source_path = Path(source_path)
    path = annotation_path(source_path, ASIDE_DIR if aside_dir is None else aside_dir)
    if not path.exists():
        if allow_missing:
            return []
        raise ValueError(f'{_relative(source_path, root)}: missing aside annotation {path}; '
                         'create one (transcript_asides.new_annotation) even if it marks nothing')
    annotation = json.loads(path.read_text(encoding='utf-8'))
    return parse_asides(annotation, source_path.read_text(encoding='utf-8'), _relative(source_path, root))


def strip_asides(text, spans):
    """Replace aside spans with ASIDE_BREAK, preserving line numbering.

    The marker is a hard boundary: metrics must not let a five-gram, an
    ordered-match run, an exact line, or an extracted clause span it, because
    the words on either side were never adjacent in the broadcast. A line with
    no words left holds only the marker, so neighbouring lines are not joined
    across a removed whole line either.
    """
    if not spans:
        return text
    lines = text.splitlines()
    by_line = {}
    for span in spans:
        by_line.setdefault(span.line, []).append(span)
    for number, line_spans in by_line.items():
        line = lines[number - 1]
        for span in sorted(line_spans, key=lambda s: s.start, reverse=True):
            line = line[:span.start] + f' {ASIDE_BREAK} ' + line[span.end:]
        line = re.sub(rf'{ASIDE_BREAK}(?:\s*{ASIDE_BREAK})+', ASIDE_BREAK, line)
        line = re.sub(r'\s{2,}', ' ', line).strip()
        lines[number - 1] = line if WORD.search(line) else ASIDE_BREAK
    return '\n'.join(lines) + ('\n' if text.endswith('\n') else '')


def break_segments(text):
    """Split metric text at aside boundaries; pieces never join across them."""
    return text.split(ASIDE_BREAK)


def metric_source_text(source_path, root=ROOT, aside_dir=None, allow_missing=False):
    """Source text as every alignment metric sees it: asides removed like breaks."""
    source_path = Path(source_path)
    return strip_asides(source_path.read_text(encoding='utf-8'),
                        load_asides(source_path, root, aside_dir, allow_missing))


def new_annotation(source_path, root=ROOT):
    """Skeleton annotation (path and hash) for a source with no asides yet."""
    source_path = Path(source_path)
    return {'source_file': _relative(source_path, root),
            'source_sha256': hashlib.sha256(source_path.read_bytes()).hexdigest(),
            'asides': []}


def summarize(root=ROOT, aside_dir=None):
    """Per-source and per-category counts of aside entries (spans) and words."""
    from sleep_baseball_corpus import corpus_paths

    rows = []
    for path in corpus_paths(root):
        lines = path.read_text(encoding='utf-8').splitlines()
        spans = load_asides(path, root, aside_dir)
        categories = {}
        seen = set()
        for span in spans:
            counts = categories.setdefault(span.category, {'spans': 0, 'words': 0})
            counts['spans'] += span.entry not in seen
            counts['words'] += len(span.words(lines))
            seen.add(span.entry)
        total_words = sum(len(re.findall(r'\w+', line)) for line in lines)
        rows.append({'source_file': _relative(path, root), 'source_words': total_words,
                     'aside_spans': len({span.entry for span in spans}),
                     'aside_words': sum(c['words'] for c in categories.values()),
                     'categories': categories})
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    rows = summarize()
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    totals = {}
    for row in rows:
        share = row['aside_words'] / row['source_words'] if row['source_words'] else 0
        print(f"{row['source_file']}: {row['aside_spans']} spans, {row['aside_words']} words ({share:.1%})")
        for category, counts in row['categories'].items():
            total = totals.setdefault(category, {'spans': 0, 'words': 0})
            total['spans'] += counts['spans']
            total['words'] += counts['words']
    print('By category: ' + '; '.join(f"{c} {t['spans']} spans/{t['words']} words"
                                      for c, t in sorted(totals.items())))


if __name__ == '__main__':
    main()
