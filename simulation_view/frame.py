"""
Frame: 2D character grid used as the source of truth for rendering.

A Frame is a height x width list of lists, where each cell contains exactly
one printable character.  Empty space is ' ' (space), never None.

Invariants:
    len(frame) == height
    len(frame[y]) == width   for all y
"""

from __future__ import annotations

Frame = list[list[str]]


def make_frame(width: int, height: int) -> Frame:
    """Create a blank frame filled with spaces."""
    return [[" " for _ in range(width)] for _ in range(height)]


def stamp(frame: Frame, row: int, col: int, text: str) -> None:
    """Write *text* into *frame* at (*row*, *col*), clipping at boundaries."""
    if row < 0 or row >= len(frame):
        return
    width = len(frame[row])
    for i, ch in enumerate(text):
        c = col + i
        if c >= width:
            break
        if c >= 0:
            frame[row][c] = ch


def frame_to_string(frame: Frame) -> str:
    """Convert a frame to a human-readable string (for debugging / tests only)."""
    return "\n".join("".join(row) for row in frame)
