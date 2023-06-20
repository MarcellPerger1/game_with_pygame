from __future__ import annotations

import cProfile
import tracemalloc

from .mem_profile import MemProf


DEBUG_MEMORY = False
# only triggered by key press so can be on by default
DEBUG_CPU = True


class PerfMgr:
    mem_snapshot: tracemalloc.Snapshot | None = None
    curr_cpu_profile: cProfile.Profile | None = None

    def __init__(self, memory=DEBUG_MEMORY, cpu=DEBUG_CPU):
        self.do_memory = memory
        self.do_cpu = cpu
        self.mem_prof = MemProf(self.do_memory)

    def take_snapshot(self):
        self.mem_snapshot = self.mem_prof.take_snapshot()

    def print_snapshot(self, *args, **kwargs):
        self.mem_prof.display_top(self.mem_snapshot, *args, **kwargs)

    def create_cpu_profile(self):
        if self.do_cpu:
            self.curr_cpu_profile = cProfile.Profile()
