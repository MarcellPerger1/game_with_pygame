from __future__ import annotations

from typing import TypeVar


T = TypeVar('T')


def option(v: T | None, default: T) -> T:
    if v is None:
        return default
    return v
