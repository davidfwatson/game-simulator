# MLB Pitch Zone Research

Research into MLB pitch distributions and Statcast zones confirms the following patterns, which are now modeled in the simulation:

## Zone Definitions (Catcher's Perspective)

*   **In-Zone (Strikes):** Zones 1-9
    *   **Corners:** 1, 3, 7, 9 (High/Low & Inside/Outside)
    *   **Edges:** 2, 4, 6, 8 (Top, Left, Right, Bottom)
    *   **Heart:** 5 (Center)
*   **Out-of-Zone (Balls):** Zones 11-14
    *   **11:** High (Arm-side for LHP, Glove-side for RHP - but generally simplified as High/Left in many views)
    *   **12:** High (Opposite of 11)
    *   **13:** Low (Arm-side for LHP, Glove-side for RHP)
    *   **14:** Low (Opposite of 13)

## Probability Distributions

### Strikes (In-Zone)
Pitchers generally target the corners and edges to avoid the "heart" of the plate where batters have the highest expected wOBA (xwOBACON).
*   **High Probability:** Zones 1, 3, 7, 9 (Corners) ~15% relative weight each.
*   **Medium Probability:** Zones 2, 4, 6, 8 (Edges) ~10% relative weight each.
*   **Low Probability:** Zone 5 (Heart) ~6% relative weight. Pitchers try to avoid this, though misses often land here.

### Balls (Out-of-Zone)
Gravity affects all pitches, and breaking balls (sliders, curveballs, changeups) are designed to drop. Therefore, misses in the dirt (Low) are significantly more common than misses high or wide, although "high heat" (fastballs) account for a good portion of high misses (chase pitches).
*   **High Probability (Low):** Zones 13 & 14. Combined weight ~60% of balls.
    *   Common for: Curveballs, Sliders, Changeups, Sinkers.
*   **Medium Probability (High):** Zones 11 & 12. Combined weight ~40% of balls.
    *   Common for: Four-seam fastballs (high chase).

## Simulation Implementation
The `BaseballSimulator` uses a weighted random choice based on these findings:
*   **Strike Logic:** `weights=[1.5, 1.0, 1.5, 1.0, 0.6, 1.0, 1.5, 1.0, 1.5]` for zones 1-9.
*   **Ball Logic:** `weights=[2.0, 2.0, 3.0, 3.0]` for zones 11-14.

This results in realistic commentary where "in the dirt" (Low) calls are more frequent than "sails high" calls, aligning with actual game data.
