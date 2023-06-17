from __future__ import annotations

import random
from typing import TypeVar

T = TypeVar('T')


def option(v: T | None, default: T) -> T:
    if v is None:
        return default
    return v


def uniform_from_mean(mean: float, size: float,
                      rng: random.Random = random) -> float:
    return rng.uniform(mean - size, mean + size)
