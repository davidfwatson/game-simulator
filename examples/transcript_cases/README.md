# Transcript situation snapshots

These fixtures cover 78 representative commentary situations from all 17 source
transcripts in `transcripts/sleep_baseball`. They test individual production
renderer helpers; they do not reconstruct complete games or measure how closely
a generated game matches an entire transcript.

Each episode has a JSON fixture and a text snapshot. Case ids identify the
reviewed authoring entries in `transcript_cases/episode_NNN.json`. The fixtures
retain source line numbers, a source-file hash, situation inputs, and four
explicit commentary draw streams. Expected phrases must occur as contiguous,
ordered words in both the source line and the rendered result, ignoring only
case and punctuation. Text snapshots additionally preserve exact rendered text.

Regenerate after reviewing intended wording or routing changes:

```sh
python update_transcript_examples.py
```

Verify existing fixtures without changing their draws or snapshots:

```sh
python update_transcript_examples.py --check
python -m unittest test_transcript_comparison
```

The compiler can select a requested template only when the actual helper offers
it for those inputs. Regression tests replay the stored integers using the
production `ChoiceRNG`; they do not select templates by their expected text.
Every source episode and authored case must be represented, and every recorded
draw must be consumed exactly once during replay.
Register each new episode and its reviewed case minimum in
`TRANSCRIPT_CASE_MINIMUMS` in `pbp_comparison.py`; existing minimums must not shrink.
