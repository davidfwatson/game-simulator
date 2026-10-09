"""Commentary choices, independent of event timing and simulation randomness.

Fixtures may store a list of whole integer draws for each commentary stream.
Unlike the old packed timestamp encoding, calls never share digits and lists
have no length limit. Unspecified draws use a deterministic PRNG.
"""

import random

from commentary import TEMPLATE_WEIGHTS


def template_weights(seq):
    """Relative weights of a pool's templates, or None when all are equal.

    ``TEMPLATE_WEIGHTS`` maps a template to its weight; every other option
    weighs 1. A pool without a weighted template is drawn exactly as before.
    """
    weights = None
    for index, option in enumerate(seq):
        weight = TEMPLATE_WEIGHTS.get(option) if isinstance(option, str) else None
        if weight is not None:
            if weights is None:
                weights = [1.0] * len(seq)
            weights[index] = weight
    return weights

# "optional" holds only the gates that decide whether an optional sentence is
# said at all (NarrativeRenderer._optional). Keeping them in their own stream
# means saying or dropping such a sentence never shifts a draw in the others.
STREAM_NAMES = ("play", "pitch", "flow", "color", "optional")


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
        return seq[self.choice_index(seq)]

    def choice_index(self, seq):
        """The index ``choice`` picks: an explicit draw modulo the pool size,
        or the weighted fallback when the fixture has no draw left."""
        if not seq:
            raise IndexError("Cannot choose from an empty sequence")
        weights = template_weights(seq)
        if weights is None:
            fallback = self.fallback.choice(range(len(seq)))
        else:
            # Templates measured as rarer (or commoner) than an average member
            # of their pool. Only the unseeded fallback is weighted: an
            # explicit draw still indexes the pool, so fixtures and the fitter
            # see every option exactly once.
            fallback = self.fallback.choices(range(len(seq)), weights)[0]
        draw = self._draw()
        return fallback if draw is None else draw % len(seq)

    def random(self):
        fallback = self.fallback.random()
        draw = self._draw()
        return fallback if draw is None else (draw % 100) / 100.0
