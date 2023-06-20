from __future__ import annotations

import linecache
import tracemalloc
from pathlib import Path

from util import fmt_size


def display_top(s: tracemalloc.Snapshot, key_type='lineno', limit=5,
                filter_imports=False, full_path=True, disp_dir_depth=2):
    if filter_imports:
        s = s.filter_traces((
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        ))
    top_stats = s.statistics(key_type)

    print(f"Top {limit} lines")
    for index, stat in enumerate(top_stats[:limit]):
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        short_name = Path(*Path(frame.filename).parts[-disp_dir_depth:])
        print(f"#{index + 1}: {short_name}:{frame.lineno}: {fmt_size(stat.size)}"
              f" (count={stat.count}, avg={fmt_size(stat.size / stat.count)})")
        if full_path:
            print(f"    {stat}")
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print(f'        {line}')

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print(f"{len(other)} other: {fmt_size(size)}")
    total = sum(stat.size for stat in top_stats)
    print(f"Total allocated size: {fmt_size(total)}")


class MemProf:
    def __init__(self, debug_memory=True, start=True):
        self.debug_memory = debug_memory
        self.snapshot = None
        if start:
            self.start()

    def start(self):
        if self.debug_memory:
            tracemalloc.start()

    def take_snapshot(self):
        self.snapshot = tracemalloc.take_snapshot() if self.debug_memory else None
        return self.snapshot

    def display_top(self, *args, **kwargs):
        if self.snapshot is not None:
            display_top(self.snapshot, *args, **kwargs)
