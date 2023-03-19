#  Copyright (c) 2023 Marcell Perger
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in all
#  copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#  SOFTWARE.
"""Not actually part of this game but I wanted to include it somewhere"""

from __future__ import annotations

import io
import itertools
import os
import typing
from dataclasses import dataclass, field
from pathlib import Path

BUFFER_SIZE = 2**16


def _partition_file(f: io.BytesIO | typing.BinaryIO):
    r = f.raw.read
    buf = r(BUFFER_SIZE)
    while buf:
        yield buf
        buf = r(BUFFER_SIZE)


def count_file_lines(p: str | Path):
    with open(p, "rb") as f:
        return sum(buf.count(b'\n') for buf in _partition_file(f)) + 1


def count_dir_lines(p: str | Path,
                    cb: typing.Callable[[Path, int], None] = lambda _p, _n, /: None,
                    cb_start: typing.Callable[[Path], None] = lambda _p: None):
    total = 0
    p = Path(p)
    for sub in p.iterdir():
        total += count_lines(sub, cb, cb_start)
    return total


def count_lines(p: str | Path,
                cb: typing.Callable[[Path, int], None] = lambda _p, _n, /: None,
                cb_start: typing.Callable[[Path], None] = lambda _p: None):
    total = 0
    p = Path(p)
    if _do_ignore(p):
        return 0
    cb_start(p)
    if p.is_file():
        total += count_file_lines(p)
    if p.is_dir():
        total += count_dir_lines(p, cb, cb_start)
    cb(p, total)
    return total


def _do_ignore(p: Path):
    if p.name in ('venv', '.git', '.idea', '.gitignore', 'game_perf.prof',
                  'LICENSE', '__pycache__'):
        return True
    return False


@dataclass
class _FsObjLines:
    path: Path
    parent: _DirLines | None
    count: int | None = None
    percent: float = None

    @property
    def is_root(self):
        return self.parent is None

    @property
    def depth(self):
        d = 0
        o = self
        while o.parent:
            o = o.parent
            d += 1
        return d


@dataclass
class _FileLines(_FsObjLines):
    pass


@dataclass
class _DirLines(_FsObjLines):
    children: list[_DirLines | _FileLines] = field(default_factory=list)


def count_lines_stats(root: Path | str, key: str = 'name', reverse: bool = None,
                      space_mode: int | None = None, sep: str | None = None,
                      dirs_mode: str = 'first'):
    root = Path(root)
    root_o = curr = _DirLines(root, None)

    def cb_start(p: Path):
        nonlocal curr
        if p.samefile(root):
            return
        new = _DirLines(p, curr) if p.is_dir() else _FileLines(p, curr)
        curr.children.append(new)
        curr = new

    def cb(p: Path, n: int):
        nonlocal curr
        curr.count = n
        path_to_obj[p] = curr
        if curr.parent:
            curr = curr.parent

    path_to_obj: dict[Path, _DirLines | _FileLines] = {}

    total = count_lines(root, cb, cb_start)

    max_len_p = len('File path')
    max_len_n = len('Lines')
    for p2, o in path_to_obj.items():
        o.percent = o.count / total * 100
        if space_mode is None:
            # for the extra ./
            max_len_p = max(len(str(p2)) + 2, max_len_p)
        else:
            max_len_p = max(len(p2.name) + space_mode * o.depth, max_len_p)
        max_len_n = max(len(str(o.count)), max_len_n)
    lengths = (max_len_p, max_len_n)

    disp_header(lengths)
    disp(root_o, lengths, 0, key, reverse, space_mode, sep, dirs_mode)

    return total


def disp(o: _DirLines | _FileLines, lengths: tuple[int, int], spaces: int = 0,
         key: str = 'name', reverse: bool = None, space_mode: int | None = None,
         sep: str | None = None, dirs_mode: str = 'first'):
    if isinstance(o, _DirLines):
        disp_dir(o, lengths, spaces, key, reverse, space_mode, sep, dirs_mode)
    else:
        disp_file(o, lengths, spaces, sep)


def disp_dir(do: _DirLines, lengths: tuple[int, int], spaces: int = 0,
             key: str = 'name', reverse: bool = None, space_mode: int | None = None,
             sep: str | None = None, dirs_mode: str = 'first'):
    disp_entry(str(do.path) + os.sep, do.count, do.percent, spaces, lengths, sep)
    spaces += len(str(do.path)) + 1 if space_mode is None else space_mode
    if key == 'name':
        key_fn = (lambda c: c.path.name.lower())
    elif key == 'lines':
        key_fn = (lambda c: c.count)
    else:
        key_fn = None
    if reverse is None:
        reverse = key == 'lines'
    if dirs_mode in ('first', 'last'):
        dirs = sorted((c for c in do.children if isinstance(c, _DirLines)),
                      key=key_fn, reverse=reverse)
        files = sorted((c for c in do.children if not isinstance(c, _DirLines)),
                       key=key_fn, reverse=reverse)
        if dirs_mode == 'first':
            it = itertools.chain(dirs, files)
        else:
            it = itertools.chain(files, dirs)
    else:
        it = sorted((c for c in do.children), key=key_fn, reverse=reverse)
    for sub in it:
        disp(sub, lengths, spaces, key, reverse, space_mode, sep)


def disp_file(fo: _FileLines, lengths: tuple[int, int],
              spaces: int = 0, sep: str | None = None):
    disp_entry(str(fo.path.name), fo.count, fo.percent, spaces, lengths, sep)


def disp_entry(path_s: str, n: int, percent: float, spaces: int,
               lengths: tuple[int, int], sep: str | None = None):
    if sep is not None:
        path_s = path_s.replace('\\', sep).replace('/', sep)
    print('| ' + (spaces * ' ' + path_s).ljust(lengths[0], ' ')
          + ' | ' + str(n).rjust(lengths[1])
          + f' | {percent:>7.1f} |')


def disp_header(lengths: tuple[int, int]):
    print('| ' + 'File path'.center(lengths[0])
          + ' | ' + 'Lines'.center(lengths[1])
          + ' | Percent |')
    print('| ' + '-' * lengths[0]
          + ' | ' + '-' * lengths[1]
          + ' | ' + '-' * 7 + ' |')


if __name__ == '__main__':
    count_lines_stats('.', sep='/', key='lines', dirs_mode='normal')
