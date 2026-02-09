"""
TerminalRenderer: stateful renderer that diffs frames and writes ANSI updates.

This is the ONLY component that mutates the terminal.  It holds the previous
frame, computes cell-level diffs, and emits batched ANSI cursor-move + write
sequences in a single ``sys.stdout.write`` + ``flush`` per draw call.

Screen clearing happens ONLY on:
  - First render (no previous frame)
  - Terminal resize (frame dimensions changed)
"""

from __future__ import annotations

import sys

from .frame import Frame

# ANSI escape helpers
_CSI = "\033["
_CLEAR_SCREEN = f"{_CSI}2J"
_CURSOR_HOME = f"{_CSI}H"
_HIDE_CURSOR = f"{_CSI}?25l"
_SHOW_CURSOR = f"{_CSI}?25h"


def _move_cursor(row: int, col: int) -> str:
    """Return ANSI sequence to move cursor to 1-based (row, col)."""
    return f"{_CSI}{row};{col}H"


class TerminalRenderer:
    def __init__(self) -> None:
        self._prev_frame: Frame | None = None
        self._cursor_hidden: bool = False

    def draw(self, frame: Frame) -> None:
        """Render *frame* to the terminal, diffing against the previous frame."""
        height = len(frame)
        width = len(frame[0]) if height > 0 else 0

        buf: list[str] = []

        if not self._cursor_hidden:
            buf.append(_HIDE_CURSOR)
            self._cursor_hidden = True

        needs_full_draw = self._needs_full_draw(frame)

        if needs_full_draw:
            buf.append(_CLEAR_SCREEN)
            buf.append(_CURSOR_HOME)
            self._draw_full(frame, height, width, buf)
        else:
            assert self._prev_frame is not None
            self._draw_diff(frame, self._prev_frame, height, width, buf)

        # Single write + single flush
        if buf:
            sys.stdout.write("".join(buf))
            sys.stdout.flush()

        # Store a copy for next diff
        self._prev_frame = [row[:] for row in frame]

    def cleanup(self) -> None:
        """Restore terminal state (show cursor)."""
        if self._cursor_hidden:
            sys.stdout.write(_SHOW_CURSOR)
            sys.stdout.flush()
            self._cursor_hidden = False

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _needs_full_draw(self, frame: Frame) -> bool:
        if self._prev_frame is None:
            return True
        height = len(frame)
        width = len(frame[0]) if height > 0 else 0
        prev_height = len(self._prev_frame)
        prev_width = len(self._prev_frame[0]) if prev_height > 0 else 0
        return height != prev_height or width != prev_width

    @staticmethod
    def _draw_full(
        frame: Frame, height: int, width: int, buf: list[str]
    ) -> None:
        """Emit every row of the frame (used on first draw or resize)."""
        for y in range(height):
            buf.append(_move_cursor(y + 1, 1))
            buf.append("".join(frame[y]))

    @staticmethod
    def _draw_diff(
        frame: Frame,
        prev: Frame,
        height: int,
        width: int,
        buf: list[str],
    ) -> None:
        """Emit only changed cells, batching consecutive changes per row."""
        for y in range(height):
            row = frame[y]
            prev_row = prev[y]
            x = 0
            while x < width:
                if row[x] != prev_row[x]:
                    # Start of a changed run
                    run_start = x
                    run: list[str] = []
                    while x < width and row[x] != prev_row[x]:
                        run.append(row[x])
                        x += 1
                    buf.append(_move_cursor(y + 1, run_start + 1))
                    buf.append("".join(run))
                else:
                    x += 1
