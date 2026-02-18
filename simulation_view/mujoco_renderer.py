"""
MuJoCo renderer for the robot simulation.

Positions robots in a 3D scene by writing data.qpos directly — no physics
step is ever called. mj_forward() updates the scene for the passive viewer.

Coordinate mapping:
    grid (col, row) → world (wx, wy, wz)
        wx = col * CELL_SIZE
        wy = -(row * CELL_SIZE)   # negate: grid-y-down → world-y-up
        wz = ROBOT_Z              # constant height

On macOS, mjpython only allows launch_passive to be called once per process.
To avoid ever reopening the viewer, the model is built once at startup with
ALL tasks included (named geoms). Completed tasks are hidden by moving their
geom below the ground plane (z = -100) rather than rebuilding the model.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import mujoco
import mujoco.viewer

from simulation_models.position import Position
from simulation_models.task_state import TaskStatus
from simulation_models.zone import ZoneType

if TYPE_CHECKING:
    from simulation_models.snapshot import SimulationSnapshot

CELL_SIZE: float = 1.0
ROBOT_Z: float = 0.3
_HIDDEN_Z: float = -100.0  # below ground; hides a geom from view

# 8-color palette for robots (RGBA, values 0–1)
_ROBOT_COLORS: list[tuple[float, float, float, float]] = [
    (0.22, 0.53, 0.96, 1.0),  # blue
    (0.95, 0.36, 0.32, 1.0),  # red
    (0.30, 0.78, 0.47, 1.0),  # green
    (0.96, 0.70, 0.20, 1.0),  # amber
    (0.67, 0.37, 0.96, 1.0),  # purple
    (0.20, 0.87, 0.87, 1.0),  # cyan
    (0.95, 0.55, 0.20, 1.0),  # orange
    (0.96, 0.37, 0.73, 1.0),  # pink
]

# Zone tile colors by type (RGBA)
_ZONE_COLORS: dict[ZoneType, tuple[float, float, float, float]] = {
    ZoneType.INSPECTION:  (0.20, 0.45, 0.85, 0.55),  # blue
    ZoneType.CHARGING:    (0.25, 0.75, 0.35, 0.55),  # green
    ZoneType.MAINTENANCE: (0.90, 0.55, 0.15, 0.55),  # orange
    ZoneType.LOADING:     (0.15, 0.70, 0.70, 0.55),  # teal
    ZoneType.RESTRICTED:  (0.85, 0.20, 0.20, 0.55),  # red
}


def _rgba_str(c: tuple[float, float, float, float]) -> str:
    return f"{c[0]:.3f} {c[1]:.3f} {c[2]:.3f} {c[3]:.3f}"


def _build_mjcf_xml(snapshot: "SimulationSnapshot") -> str:
    """
    Build the MJCF XML string from the initial snapshot.

    All tasks are included regardless of status so the model never needs
    rebuilding. Each task marker geom is named 'task_marker_{task_id}'.
    """
    env = snapshot.env

    cx = (env.width - 1) * CELL_SIZE / 2.0
    cy = -((env.height - 1) * CELL_SIZE / 2.0)
    gw = env.width * CELL_SIZE
    gh = env.height * CELL_SIZE

    lines: list[str] = []
    lines.append('<mujoco model="robot_sim">')
    lines.append('  <option gravity="0 0 -9.81"/>')
    lines.append('  <visual><headlight diffuse="0.8 0.8 0.8" specular="0.2 0.2 0.2"/></visual>')
    lines.append('  <worldbody>')

    # Ground plane
    lines.append(
        f'    <geom name="ground" type="plane"'
        f' pos="{cx:.3f} {cy:.3f} 0"'
        f' size="{gw/2:.3f} {gh/2:.3f} 0.1"'
        f' rgba="0.55 0.55 0.55 1" contype="1" conaffinity="1"/>'
    )

    # Directional light
    lines.append(
        '    <light name="sun" directional="true"'
        ' pos="0 0 10" dir="0 -0.3 -1"'
        ' diffuse="0.9 0.9 0.9" specular="0.3 0.3 0.3"/>'
    )

    # Zone tiles (flat boxes, visual-only)
    for zone in env._zones.values():
        color = _ZONE_COLORS.get(zone.zone_type, (0.5, 0.5, 0.5, 0.4))
        rgba = _rgba_str(color)
        for pos in zone.cells:
            wx = pos.x * CELL_SIZE
            wy = -(pos.y * CELL_SIZE)
            lines.append(
                f'    <geom type="box"'
                f' pos="{wx:.3f} {wy:.3f} 0.01"'
                f' size="{CELL_SIZE/2:.3f} {CELL_SIZE/2:.3f} 0.01"'
                f' rgba="{rgba}" contype="0" conaffinity="0"/>'
            )

    # Obstacles (grey boxes, collidable)
    for pos in env.obstacles:
        wx = pos.x * CELL_SIZE
        wy = -(pos.y * CELL_SIZE)
        lines.append(
            f'    <geom type="box"'
            f' pos="{wx:.3f} {wy:.3f} 0.25"'
            f' size="{CELL_SIZE/2:.3f} {CELL_SIZE/2:.3f} 0.25"'
            f' rgba="0.35 0.35 0.35 1" contype="1" conaffinity="1"/>'
        )

    # Task markers: ALL tasks included (named so we can hide completed ones).
    # Tasks without a Position target have no marker.
    for task in snapshot.tasks:
        sc = task.spatial_constraint
        if sc is None or not isinstance(sc.target, Position):
            continue
        wx = sc.target.x * CELL_SIZE
        wy = -(sc.target.y * CELL_SIZE)
        lines.append(
            f'    <geom name="task_marker_{int(task.id)}" type="cylinder"'
            f' pos="{wx:.3f} {wy:.3f} 0.03"'
            f' size="{CELL_SIZE*0.35:.3f} 0.03"'
            f' rgba="1.0 0.85 0.0 0.85" contype="0" conaffinity="0"/>'
        )

    # Robot bodies (sorted by id for stable qpos indexing)
    robots_sorted = sorted(snapshot.robots, key=lambda r: int(r.id))
    for i, robot in enumerate(robots_sorted):
        state = snapshot.robot_states[robot.id]
        wx = state.position.x * CELL_SIZE
        wy = -(state.position.y * CELL_SIZE)
        color = _ROBOT_COLORS[i % len(_ROBOT_COLORS)]
        rgba = _rgba_str(color)
        lines.append(
            f'    <body name="robot_{int(robot.id)}"'
            f' pos="{wx:.3f} {wy:.3f} {ROBOT_Z:.3f}">'
        )
        lines.append('      <freejoint/>')
        lines.append(
            f'      <geom type="sphere" size="{CELL_SIZE*0.28:.3f}"'
            f' rgba="{rgba}" contype="0" conaffinity="0"/>'
        )
        lines.append('    </body>')

    lines.append('  </worldbody>')
    lines.append('</mujoco>')
    return "\n".join(lines)


class MuJoCoRenderer:
    """
    Passive MuJoCo viewer renderer.

    The model is built exactly once from the initial snapshot. Completed task
    markers are hidden by moving their geom to z=-100 (below ground) rather
    than rebuilding the model, so launch_passive is only ever called once —
    required on macOS under mjpython.
    """

    def __init__(self) -> None:
        self._model: mujoco.MjModel | None = None
        self._data: mujoco.MjData | None = None
        self._viewer = None
        # task_id (int) → geom index in model; only for tasks with Position targets
        self._task_geom_ids: dict[int, int] = {}

    def update(self, snapshot: "SimulationSnapshot") -> None:
        """Update robot positions and task marker visibility; sync viewer."""
        if self._model is None:
            self._build_model(snapshot)

        self._update_task_markers(snapshot)
        self._sync_robot_positions(snapshot)
        mujoco.mj_forward(self._model, self._data)

        if self._viewer is None or not self._viewer.is_running():
            self._viewer = mujoco.viewer.launch_passive(self._model, self._data)
        else:
            self._viewer.sync()

    def wait_for_close(self) -> None:
        """Block until the user closes the viewer window."""
        if self._viewer is None:
            return
        while self._viewer.is_running():
            self._viewer.sync()

    def cleanup(self) -> None:
        """Close viewer window if open."""
        if self._viewer is not None:
            try:
                self._viewer.close()
            except Exception:
                pass
            self._viewer = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_model(self, snapshot: "SimulationSnapshot") -> None:
        xml = _build_mjcf_xml(snapshot)
        self._model = mujoco.MjModel.from_xml_string(xml)
        self._data = mujoco.MjData(self._model)

        # Cache geom indices for task markers so we can hide/show them
        for task in snapshot.tasks:
            sc = task.spatial_constraint
            if sc is None or not isinstance(sc.target, Position):
                continue
            name = f"task_marker_{int(task.id)}"
            gid = mujoco.mj_name2id(self._model, mujoco.mjtObj.mjOBJ_GEOM, name)
            if gid >= 0:
                self._task_geom_ids[int(task.id)] = gid

    def _update_task_markers(self, snapshot: "SimulationSnapshot") -> None:
        """Hide completed/failed task markers by moving them below ground."""
        for task in snapshot.tasks:
            gid = self._task_geom_ids.get(int(task.id))
            if gid is None:
                continue
            state = snapshot.task_states[task.id]
            if state.status in (TaskStatus.DONE, TaskStatus.FAILED):
                self._model.geom_pos[gid, 2] = _HIDDEN_Z
            else:
                self._model.geom_pos[gid, 2] = 0.03  # restore to ground level

    def _sync_robot_positions(self, snapshot: "SimulationSnapshot") -> None:
        """Write robot positions into qpos (7 DOF per robot: x,y,z,qw,qx,qy,qz)."""
        robots_sorted = sorted(snapshot.robots, key=lambda r: int(r.id))
        for i, robot in enumerate(robots_sorted):
            state = snapshot.robot_states[robot.id]
            base = i * 7
            self._data.qpos[base + 0] = state.position.x * CELL_SIZE
            self._data.qpos[base + 1] = -(state.position.y * CELL_SIZE)
            self._data.qpos[base + 2] = ROBOT_Z
            self._data.qpos[base + 3] = 1.0  # quaternion w (identity)
            self._data.qpos[base + 4] = 0.0
            self._data.qpos[base + 5] = 0.0
            self._data.qpos[base + 6] = 0.0
