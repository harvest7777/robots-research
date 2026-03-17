import pytest

from simulation.domain.environment import Environment, Obstacle
from simulation.domain.rescue_point import RescuePoint
from simulation.domain.task import TaskId, SpatialConstraint
from simulation.primitives.position import Position
from simulation.primitives.zone import Zone, ZoneId, ZoneType


def _env(width: int = 5, height: int = 5) -> Environment:
    return Environment(width=width, height=height)


def _zone(zone_id: int, *positions: Position) -> Zone:
    return Zone.from_positions(
        id=ZoneId(zone_id),
        zone_type=ZoneType.INSPECTION,
        positions=positions,
    )


def _rescue_point(pos: Position) -> RescuePoint:
    return RescuePoint(
        id=TaskId(1),
        priority=5,
        spatial_constraint=SpatialConstraint(target=pos, max_distance=0),
        name="rp1",
    )


# ---------------------------------------------------------------------------
# place / get_at
# ---------------------------------------------------------------------------

def test_place_accepts_valid_position():
    env = _env()
    sentinel = object()
    env.place(Position(2, 3), sentinel)
    assert env.get_at(Position(2, 3)) is sentinel


def test_place_rejects_out_of_bounds():
    env = _env(width=5, height=5)
    with pytest.raises(IndexError):
        env.place(Position(-1, 0), object())
    with pytest.raises(IndexError):
        env.place(Position(0, -1), object())
    with pytest.raises(IndexError):
        env.place(Position(5, 0), object())
    with pytest.raises(IndexError):
        env.place(Position(0, 5), object())


def test_place_rejects_occupied_cell():
    env = _env()
    pos = Position(1, 1)
    env.place(pos, object())
    with pytest.raises(ValueError):
        env.place(pos, object())


# ---------------------------------------------------------------------------
# in_bounds
# ---------------------------------------------------------------------------

def test_in_bounds_corners():
    env = _env(width=5, height=5)
    assert env.in_bounds(Position(0, 0))
    assert env.in_bounds(Position(4, 0))
    assert env.in_bounds(Position(0, 4))
    assert env.in_bounds(Position(4, 4))


def test_in_bounds_edges():
    env = _env(width=5, height=5)
    assert env.in_bounds(Position(4, 2))
    assert env.in_bounds(Position(2, 4))
    assert not env.in_bounds(Position(5, 2))
    assert not env.in_bounds(Position(2, 5))


# ---------------------------------------------------------------------------
# add_obstacle / is_empty
# ---------------------------------------------------------------------------

def test_add_obstacle_blocks_cell():
    env = _env()
    pos = Position(2, 2)
    env.add_obstacle(pos)
    assert not env.is_empty(pos)


# ---------------------------------------------------------------------------
# add_zone / get_zone
# ---------------------------------------------------------------------------

def test_add_zone_registers_cells():
    env = _env()
    p1, p2 = Position(0, 0), Position(1, 0)
    zone = _zone(1, p1, p2)
    env.add_zone(zone)
    retrieved = env.get_zone(ZoneId(1))
    assert retrieved is not None
    assert retrieved.contains(p1)
    assert retrieved.contains(p2)


# ---------------------------------------------------------------------------
# add_rescue_point
# ---------------------------------------------------------------------------

def test_add_rescue_point_registered():
    env = _env()
    rp = _rescue_point(Position(3, 3))
    env.add_rescue_point(rp)
    assert TaskId(1) in env.rescue_points
    assert env.rescue_points[TaskId(1)] is rp


# ---------------------------------------------------------------------------
# is_empty on fresh grid
# ---------------------------------------------------------------------------

def test_is_empty_on_fresh_grid():
    env = _env(width=3, height=3)
    for y in range(3):
        for x in range(3):
            assert env.is_empty(Position(x, y))
