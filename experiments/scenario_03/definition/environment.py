# Scenario 03 — flat 20x15 grid, no obstacles, no rescue points.

from __future__ import annotations

from simulation.domain import Environment

WIDTH  = 20
HEIGHT = 15


def build_environment() -> Environment:
    return Environment(width=WIDTH, height=HEIGHT)
