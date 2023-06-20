from __future__ import annotations

import cProfile
import contextlib


class CpuProfileContextManager(contextlib.AbstractContextManager):
    def __init__(self, dump_to: str, always_dump=False):
        self.profile = cProfile.Profile()
        self.dump_to = dump_to
        self.always_dump = always_dump

    def __enter__(self):
        return self.profile.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.profile.__exit__(exc_type, exc_val, exc_tb)
        if self.always_dump or exc_type is None:
            self.profile.dump_stats(self.dump_to)
