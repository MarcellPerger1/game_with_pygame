from __future__ import annotations

import linecache
import tracemalloc
from pathlib import Path


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
              f" (count={stat.count}, avg={fmt_size(stat.size/stat.count)})")
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
        if start:
            self.start()

    def start(self):
        if self.debug_memory:
            tracemalloc.start()

    def take_snapshot(self):
        if self.debug_memory:
            s = tracemalloc.take_snapshot()
        else:
            s = tracemalloc.Snapshot([], 0)
        s.is_null = self.debug_memory
        return s

    def show_top(self, s: tracemalloc.Snapshot, *args, **kwargs):
        if not getattr(s, 'is_null', False) and self.debug_memory:
            display_top(s, *args, **kwargs)
    display_top = show_top
