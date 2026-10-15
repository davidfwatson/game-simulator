# Count shape calibration

Comparison: 136 complete 2026 MLB feeds (10,309 completed PAs), versus 1,000 games before and after, seeds 20000–20999, with BAY_BOMBERS at home and PC_PILOTS away. The baseline is commit `652bcdc`. Calibration scripts and full distributions are in the shared `scratchpad/codex/work-counts/` directory.

Count visits are counted once per completed PA. Real pitch events store the count after a pitch; simulated events store it before, so the real counts are reconstructed from preceding events. StatsAPI matchup base splits describe the end of the play, while the sim records the start; runner movements supply the starting situation for both. Pitches/PA includes pitches from unfinished PAs. Clustering uses regulation innings and overlapping complete three-inning windows (six team halves).

| Overall metric | Real | Before | After |
|---|---:|---:|---:|
| Runs/team-game | 4.445 | 4.346 | 4.425 |
| Strikeouts/PA | 21.85% | 22.30% | 21.89% |
| Walks/PA | 8.91% | 9.43% | 8.80% |
| Hits/PA | 21.90% | 21.91% | 22.55% |
| Pitches/PA | 3.874 | 3.864 | 3.886 |
| Fouls/PA | 0.723 | 0.741 | 0.752 |

| Count reached, share of PA | Real | Before | After |
|---|---:|---:|---:|
| 0-0 | 99.65% | 99.78% | 99.76% |
| 0-1 | 49.79% | 49.40% | 50.14% |
| 0-2 | 21.56% | 21.66% | 21.93% |
| 1-0 | 37.84% | 37.34% | 37.41% |
| 1-1 | 37.94% | 37.47% | 37.75% |
| 1-2 | 28.99% | 28.49% | 29.44% |
| 2-0 | 12.54% | 12.54% | 12.41% |
| 2-1 | 20.09% | 20.25% | 19.59% |
| 2-2 | 23.88% | 24.14% | 24.11% |
| 3-0 | 3.84% | 3.97% | 3.98% |
| 3-1 | 8.45% | 8.72% | 8.42% |
| 3-2 | 14.02% | 14.45% | 14.05% |

The baseline full-count excess was modest in aggregate; the larger problems were when hitters swung 3–0 and which pitchers issued walks. The change keeps rare full-count clusters possible.

| Full-count clustering | Real | Before | After |
|---|---:|---:|---:|
| Per team half, mean (SD) | 0.598 (0.763) | 0.622 (0.781) | 0.603 (0.771) |
| Per three innings, mean (SD) | 3.548 (1.864) | 3.777 (1.914) | 3.607 (1.915) |
| Per team three-inning stretch, mean (SD) | 1.757 (1.304) | 1.880 (1.355) | 1.802 (1.357) |
| Three-inning windows with 9+ full counts | 1.02% | 1.50% | 1.16% |

| Full counts per team half | Real | Before | After |
|---|---:|---:|---:|
| 0 | 54.83% | 53.27% | 54.58% |
| 1 | 32.77% | 34.07% | 33.05% |
| 2 | 10.34% | 10.30% | 10.22% |
| 3 | 1.93% | 1.97% | 1.84% |
| 4 | 0.08% | 0.37% | 0.28% |
| 5+ | 0.04% | 0.03% | 0.03% |

| 3–0 swing rate by situation | Real | Before | After |
|---|---:|---:|---:|
| All | 6.31% (396) | 8.05% (3042) | 7.34% (3051) |
| Batting lead/deficit within two runs | 9.62% (239) | 8.59% (2106) | 10.11% (1979) |
| Batting team ahead by 3+ | 2.47% (81) | 7.59% (435) | 2.63% (533) |
| Batting team behind by 3+ | 0.00% (76) | 6.19% (501) | 1.86% (539) |
| Innings 7+, ahead by 3+ | 0.00% (31) | 8.70% (161) | 2.87% (279) |
| Innings 7+, behind by 3+ | 0.00% (41) | 7.98% (188) | 2.43% (288) |
| Bases empty | 5.12% (215) | 7.39% (1718) | 6.23% (1605) |
| Runners aboard | 7.73% (181) | 8.91% (1324) | 8.58% (1446) |
| Lineup slots 3–5 | 8.15% (135) | 11.03% (1224) | 8.48% (1227) |
| Other lineup slots | 5.36% (261) | 6.05% (1818) | 6.58% (1824) |
| High extra-base rate | 11.69% (77) | 25.76% (229) | 15.75% (254) |
| Low extra-base rate | 5.13% (39) | 4.51% (1263) | 5.35% (1122) |

Parentheses give the number of 3–0 pitches, not swings. Lineup slots provide a stable quality proxy. The extra quality split uses extra bases per sampled PA with a 100-PA prior at .160; high is at least .180 and low is below .130. Those observed-quality cohorts can change between simulated batches. Small real samples with zero swings do not justify a hard take rule.

| First-pitch outcome, share of PA | Real | Before | After |
|---|---:|---:|---:|
| Ball | 37.84% | 37.43% | 37.50% |
| Called strike | 29.54% | 28.76% | 29.66% |
| Swinging strike / foul tip | 8.04% | 7.23% | 7.94% |
| Foul | 12.25% | 13.57% | 12.71% |
| In play | 11.77% | 12.80% | 11.95% |

Real first-pitch HBP is 0.30% of PA. The existing simulator does not append the HBP pitch to playEvents; that feed issue is unchanged. First-pitch shares can therefore sum to less than 100%.

| Pitcher outing metric | Real | Before | After |
|---|---:|---:|---:|
| Starter walks/PA | 8.28% | 10.89% | 8.22% |
| Reliever walks/PA | 9.70% | 7.56% | 9.55% |
| Starter BB-rate variance, BF >= 12 | 0.00457 | 0.00495 | 0.00424 |
| Starter pitches/PA variance, BF >= 12 | 0.19955 | 0.18063 | 0.19216 |
| Reliever BB-rate variance, BF >= 4 | 0.01640 | 0.01214 | 0.01548 |
| Reliever pitches/PA variance, BF >= 4 | 0.74861 | 0.71749 | 0.71599 |
| All pitcher BB-rate variance, BF >= 4 | 0.01357 | 0.01028 | 0.01207 |
| All pitcher pitches/PA variance, BF >= 4 | 0.59105 | 0.55644 | 0.55816 |
| Starters with no walks, BF >= 12 | 14.80% | 7.63% | 16.55% |
| Starter BB-rate variance above binomial baseline | 0.00112 | 0.00045 | 0.00074 |

Raw starter walk-rate variance was already close because the simulated mean walk rate was too high. Subtracting the role-level binomial baseline reveals less extra variability: this measure includes both pitcher talent and daily form. Repeated outings by the same real pitcher are too sparse here to cleanly separate those components.

In baseball.py, effective command shrinks roster ratings toward a role mean (starter .68, reliever .63, with .4 of the rating difference from .66) and adds a persistent normal outing adjustment with SD .055. A separate seeded stream draws that adjustment without consuming bullpen or other setup draws. Count zone/chase rates and a replacement contact-by-count table bring early swings, protection, walks and strikeouts into balance. The existing 3–0 green light now reads the batting side’s score and runners, retaining hitter power, location and pitch-type effects.

Seven consecutive out-producing PAs totaling at most 15 pitches occurred in 0.33% of eligible real windows (2/601), 0.58% before (20/3467), and 0.63% after (23/3669). This rare tail did not improve in this batch; the real sample is too small to support a special sequence rule. The first-pitch fair-contact rate did improve from 12.80% to 11.95%, against 11.77% real.

Foul probabilities, pitch selection, roster data, strategy, runner advancement and prose are unchanged. No example snapshots were regenerated, no transcript fixtures were refitted, and no comparison minimums were changed.

Validation: nine new focused tests cover count frequencies, full-count clustering, first pitches, pitcher walk rates and variance, persistent command, and situational 3–0 swings. The full requested unittest run reported:

```text
Ran 551 tests in 178.512s
FAILED (failures=21, skipped=9)
```

All 21 failures are expected output differences in the three snapshot tests: ten narrative examples, ten gameday examples, and the statcast snapshot test. Every other test passes. `pbp_match_report.py --check`, `full_transcript_comparison.py --check`, and `template_repetition.py --games 50 --check` all exit 0; no minimum was missed.
