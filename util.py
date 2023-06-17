from __future__ import annotations

import random
from math import inf
from typing import TypeVar

T = TypeVar('T')
NT = TypeVar('NT', bound=float)


def option(v: T | None, default: T) -> T:
    if v is None:
        return default
    return v


def uniform_from_mean(mean: float, size: float,
                      rng: random.Random = random) -> float:
    return rng.uniform(mean - size, mean + size)


def clamp(value: NT, low: NT | None = None,
          high: NT | None = None) -> NT:
    if low is None:
        low = -inf
    if high is None:
        high = inf
    return min(max(value, low), high)
