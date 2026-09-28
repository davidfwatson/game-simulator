"""Commentary choices, independent of event timing and simulation randomness.

Fixtures may store a list of whole integer draws for each commentary stream.
Unlike the old packed timestamp encoding, calls never share digits and lists
have no length limit. Unspecified draws use a deterministic PRNG.
"""

import random

STREAM_NAMES = ("play", "pitch", "flow", "color")


class ChoiceRNG:
    """Replay explicit draws, then continue with a seeded random stream.

    A choice draw is reduced modulo the current pool size; a probability draw
    uses its last two digits as hundredths. Lists are copied, never consumed
    from the source document. The fallback advances even for explicit draws,
    so overriding a draw does not shift later unspecified draws.
    """

    def __init__(self, draws, seed):
        if not isinstance(draws, list) or any(
            type(value) is not int or value < 0 for value in draws
        ):
            raise ValueError("Commentary draws must be a list of nonnegative integers")
        self.draws = tuple(draws)
        self.position = 0
        self.fallback = random.Random(seed)

    def _draw(self):
        position = self.position
        self.position += 1
        return self.draws[position] if position < len(self.draws) else None

    def choice(self, seq):
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        fallback = self.fallback.choice(seq)
        draw = self._draw()
        return fallback if draw is None else seq[draw % len(seq)]

    def random(self):
        fallback = self.fallback.random()
        draw = self._draw()
        return fallback if draw is None else (draw % 100) / 100.0

