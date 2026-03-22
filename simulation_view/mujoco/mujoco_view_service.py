import math
import random
import time

import mujoco
import mujoco.viewer

from simulation import SimulationState, TaskStatus
from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.task import WorkTask
from simulation.primitives.position import Position
from simulation.primitives.zone import ZoneType
from simulation_view.base_simulation_view import BaseViewService

CELL_SIZE = 1.5  # meters per grid cell
ANIM_SPEED = 10.0  # animation radians per real second (~1.6 leg cycles/sec)

_QPOS_PER_ROBOT = 15     # 7 (freejoint) + 8 (hinge joints, 2 per leg × 4 legs)
_QPOS_PER_MOVE_OBJ = 7  # freejoint only: 3 pos + 4 quat

ZONE_COLORS = {
    ZoneType.INSPECTION:  "0.2 0.4 0.9 0.35",
    ZoneType.MAINTENANCE: "0.9 0.5 0.1 0.35",
    ZoneType.LOADING:     "0.9 0.9 0.1 0.35",
    ZoneType.RESTRICTED:  "0.9 0.1 0.1 0.35",
    ZoneType.CHARGING:    "0.1 0.9 0.2 0.35",
}


def _to_world(x: float, y: float) -> tuple[float, float]:
    return x * CELL_SIZE, -y * CELL_SIZE


def _ant_xml(idx: int) -> str:
    p = f"a{idx}_"
    return f"""
    <body name="{p}torso" pos="0 0 0.75">
      <freejoint name="{p}root"/>
      <geom type="sphere" size="0.25" rgba="0.2 0.6 1.0 1"/>
      <body name="{p}fl" pos="0.2 0.2 0">
        <joint name="{p}fl1" type="hinge" axis="0 1 0" range="-40 40"/>
        <geom type="capsule" fromto="0 0 0 0.3 0 -0.25" size="0.06" rgba="0.2 0.4 0.8 1"/>
        <body name="{p}fl2" pos="0.3 0 -0.25">
          <joint name="{p}fl2j" type="hinge" axis="0 1 0" range="-60 -10"/>
          <geom type="capsule" fromto="0 0 0 0.2 0 -0.2" size="0.06" rgba="0.2 0.4 0.8 1"/>
        </body>
      </body>
      <body name="{p}fr" pos="0.2 -0.2 0">
        <joint name="{p}fr1" type="hinge" axis="0 1 0" range="-40 40"/>
        <geom type="capsule" fromto="0 0 0 0.3 0 -0.25" size="0.06" rgba="0.2 0.4 0.8 1"/>
        <body name="{p}fr2" pos="0.3 0 -0.25">
          <joint name="{p}fr2j" type="hinge" axis="0 1 0" range="-60 -10"/>
          <geom type="capsule" fromto="0 0 0 0.2 0 -0.2" size="0.06" rgba="0.2 0.4 0.8 1"/>
        </body>
      </body>
      <body name="{p}bl" pos="-0.2 0.2 0">
        <joint name="{p}bl1" type="hinge" axis="0 1 0" range="-40 40"/>
        <geom type="capsule" fromto="0 0 0 -0.3 0 -0.25" size="0.06" rgba="0.2 0.4 0.8 1"/>
        <body name="{p}bl2" pos="-0.3 0 -0.25">
          <joint name="{p}bl2j" type="hinge" axis="0 1 0" range="-60 -10"/>
          <geom type="capsule" fromto="0 0 0 -0.2 0 -0.2" size="0.06" rgba="0.2 0.4 0.8 1"/>
        </body>
      </body>
      <body name="{p}br" pos="-0.2 -0.2 0">
        <joint name="{p}br1" type="hinge" axis="0 1 0" range="-40 40"/>
        <geom type="capsule" fromto="0 0 0 -0.3 0 -0.25" size="0.06" rgba="0.2 0.4 0.8 1"/>
        <body name="{p}br2" pos="-0.3 0 -0.25">
          <joint name="{p}br2j" type="hinge" axis="0 1 0" range="-60 -10"/>
          <geom type="capsule" fromto="0 0 0 -0.2 0 -0.2" size="0.06" rgba="0.2 0.4 0.8 1"/>
        </body>
      </body>
    </body>"""


def _build_xml(state: SimulationState, num_robots: int) -> str:
    env = state.environment
    cx, cy = _to_world(env.width / 2, env.height / 2)
    half = CELL_SIZE / 2

    # Obstacles
    obstacle_geoms = "\n".join(
        f'    <geom type="box" pos="{_to_world(p.x, p.y)[0]} {_to_world(p.x, p.y)[1]} 0.5" '
        f'size="{half} {half} 0.5" rgba="0.4 0.3 0.2 1"/>'
        for p in env.obstacles
    )

    # Zones — one flat box per cell
    zone_geoms = "\n".join(
        f'    <geom type="box" pos="{_to_world(pos.x, pos.y)[0]} {_to_world(pos.x, pos.y)[1]} 0.02" '
        f'size="{half} {half} 0.02" rgba="{ZONE_COLORS.get(zone.zone_type, "0.5 0.5 0.5 0.3")}"/>'
        for zone in env._zones.values()
        for pos in zone.cells
    )

    # WorkTask targets — green cylinders
    work_task_geoms = "\n".join(
        f'    <geom type="cylinder" pos="{_to_world(task.spatial_constraint.target.x, task.spatial_constraint.target.y)[0]} '
        f'{_to_world(task.spatial_constraint.target.x, task.spatial_constraint.target.y)[1]} 0.05" '
        f'size="0.3 0.05" rgba="0.1 0.8 0.2 1"/>'
        for task in state.tasks.values()
        if isinstance(task, WorkTask)
        and task.spatial_constraint is not None
        and isinstance(task.spatial_constraint.target, Position)
    )

    # Rescue points — red spheres
    rescue_geoms = "\n".join(
        f'    <geom type="sphere" pos="{_to_world(rp.position.x, rp.position.y)[0]} '
        f'{_to_world(rp.position.x, rp.position.y)[1]} 0.4" size="0.2" rgba="0.9 0.1 0.1 1"/>'
        for rp in env.rescue_points.values()
    )

    # MoveTask objects — one pre-allocated free body per rescue point, parked underground
    move_obj_bodies = "\n".join(
        f'    <body name="move_{i}" pos="0 0 -10">'
        f'<freejoint name="move_{i}_root"/>'
        f'<geom type="box" size="0.4 0.4 0.3" rgba="1.0 0.6 0.0 1"/>'
        f'</body>'
        for i in range(len(env.rescue_points))
    )

    robot_bodies = "\n".join(_ant_xml(i) for i in range(num_robots))

    return f"""<mujoco>
  <option gravity="0 0 -9.81"/>
  <visual>
    <headlight ambient="0.5 0.5 0.5" diffuse="0 0 0" specular="0 0 0"/>
  </visual>
  <worldbody>
    <light directional="true" pos="0 0 1" dir="0 0 -1" diffuse="0.6 0.6 0.6" specular="0.1 0.1 0.1" castshadow="false"/>
    <geom name="floor" type="plane" size="{env.width * CELL_SIZE} {env.height * CELL_SIZE} 0.1" rgba="0.8 0.85 0.8 1"/>
    {zone_geoms}
    {obstacle_geoms}
    {work_task_geoms}
    {rescue_geoms}
    {move_obj_bodies}
    {robot_bodies}
  </worldbody>
</mujoco>"""


class MujocoViewService(BaseViewService):

    def __init__(self):
        self._model = None
        self._data = None
        self._viewer = None
        self._robot_ids = []
        self._prev_positions = {}
        self._anim_time = 0.0
        self._last_render_time = None
        self._leg_params: dict = {}
        # MoveTask slot: task_id -> index into pre-allocated move bodies
        self._move_task_slots: dict = {}
        # qpos offset where move object data starts
        self._move_obj_qpos_start = 0

    def _get_leg_params(self, robot_id):
        if robot_id not in self._leg_params:
            self._leg_params[robot_id] = [
                (random.uniform(0.8, 1.4), random.uniform(0, 2 * math.pi))
                for _ in range(8)
            ]
        return self._leg_params[robot_id]

    def render(self, simulation_state: SimulationState) -> None:
        if self._model is None:
            self._init_scene(simulation_state)

        if not self._viewer.is_running():
            return

        now = time.time()
        dt = now - self._last_render_time if self._last_render_time else 0.0
        self._last_render_time = now
        self._anim_time += dt * ANIM_SPEED

        self._update_robots(simulation_state)
        self._update_move_objects(simulation_state)

        mujoco.mj_forward(self._model, self._data)
        self._viewer.sync()

    def handle_exit(self):
        if self._viewer is not None:
            self._viewer.close()

    def _init_scene(self, state: SimulationState) -> None:
        self._robot_ids = list(state.robots.keys())
        env = state.environment

        # Map each rescue point's MoveTask id to a pre-allocated slot index
        self._move_task_slots = {
            rp.task.id: i
            for i, rp in enumerate(env.rescue_points.values())
        }
        # Move object qpos starts after all robot joints
        self._move_obj_qpos_start = len(self._robot_ids) * _QPOS_PER_ROBOT

        xml = _build_xml(state, len(self._robot_ids))
        self._model = mujoco.MjModel.from_xml_string(xml)
        self._data = mujoco.MjData(self._model)
        self._viewer = mujoco.viewer.launch_passive(self._model, self._data)

    def _update_robots(self, state: SimulationState) -> None:
        for i, robot_id in enumerate(self._robot_ids):
            rs = state.robot_states.get(robot_id)
            if rs is None:
                continue

            wx, wy = _to_world(rs.position.x, rs.position.y)
            start = i * _QPOS_PER_ROBOT

            self._data.qpos[start:start + 3] = [wx, wy, 0.75]
            self._data.qpos[start + 3:start + 7] = [1, 0, 0, 0]

            is_moving = self._prev_positions.get(robot_id) != rs.position
            self._prev_positions[robot_id] = rs.position

            if is_moving:
                params = self._get_leg_params(robot_id)
                t = self._anim_time
                joints = []
                for j, (freq, phase) in enumerate(params):
                    s = math.sin(freq * t + phase)
                    if j % 2 == 0:
                        joints.append(0.5 * s)
                    else:
                        joints.append(-0.475 + 0.275 * s)
                self._data.qpos[start + 7:start + 15] = joints
            else:
                self._data.qpos[start + 7:start + 15] = [0, -0.4, 0, -0.4, 0, -0.4, 0, -0.4]

    def _update_move_objects(self, state: SimulationState) -> None:
        for task_id, slot in self._move_task_slots.items():
            start = self._move_obj_qpos_start + slot * _QPOS_PER_MOVE_OBJ
            ts = state.task_states.get(task_id)

            if ts is None or ts.status in (TaskStatus.DONE, TaskStatus.FAILED):
                # Not yet spawned or finished — park underground
                self._data.qpos[start:start + 7] = [0, 0, -10, 1, 0, 0, 0]
            else:
                assert isinstance(ts, MoveTaskState)
                wx, wy = _to_world(ts.current_position.x, ts.current_position.y)
                self._data.qpos[start:start + 7] = [wx, wy, 0.3, 1, 0, 0, 0]
