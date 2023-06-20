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


def fmt_size(sz_bytes: int | float) -> str:
    sz_bytes = int(sz_bytes)  # can't have 5.3 of a byte
    if sz_bytes < 10*1000:
        return f'{sz_bytes} B'
    prefs = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y', 'R', 'Q')
    for i, pref in enumerate(prefs):
        max_threshold = 10_000 * 1000**(i+1)  # eg. max 9999.9 KiB to use KiB
        multiplier = 1024**(i+1)
        if sz_bytes < max_threshold or i == len(pref) - 1:
            return f'{sz_bytes/multiplier:.1f} {pref}iB'
    raise AssertionError("Unreachable code has been reached")
