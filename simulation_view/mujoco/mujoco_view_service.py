import math
import random
import time

import mujoco
import mujoco.viewer

from simulation import SimulationState
from simulation_view.base_simulation_view import BaseViewService

CELL_SIZE = 1.5  # meters per grid cell
ANIM_SPEED = 10.0  # animation radians per real second (~1.6 leg cycles/sec)
_QPOS_PER_ROBOT = 15  # 7 (freejoint) + 8 (hinge joints, 2 per leg × 4 legs)


def _to_world(x: int, y: int) -> tuple[float, float]:
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


def _build_xml(num_robots: int, width: int, height: int, obstacles) -> str:
    cx, cy = _to_world(width / 2, height / 2)

    half = CELL_SIZE / 2
    obstacle_geoms = "\n".join(
        f'    <geom type="box" pos="{_to_world(p.x, p.y)[0]} {_to_world(p.x, p.y)[1]} 0.5" '
        f'size="{half} {half} 0.5" rgba="0.4 0.3 0.2 1"/>'
        for p in obstacles
    )

    robot_bodies = "\n".join(_ant_xml(i) for i in range(num_robots))

    return f"""<mujoco>
  <option gravity="0 0 -9.81"/>
  <visual>
    <headlight ambient="0.5 0.5 0.5" diffuse="0 0 0" specular="0 0 0"/>
  </visual>
  <worldbody>
    <light directional="true" pos="0 0 1" dir="0 0 -1" diffuse="0.6 0.6 0.6" specular="0.1 0.1 0.1" castshadow="false"/>
    <geom name="floor" type="plane" size="{width * CELL_SIZE} {height * CELL_SIZE} 0.1" rgba="0.8 0.85 0.8 1"/>
    {obstacle_geoms}
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
        # Per-robot: 8 joints each get an independent (frequency, phase) pair
        self._leg_params: dict = {}

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

        for i, robot_id in enumerate(self._robot_ids):
            rs = simulation_state.robot_states.get(robot_id)
            if rs is None:
                continue

            wx, wy = _to_world(rs.position.x, rs.position.y)
            start = i * _QPOS_PER_ROBOT

            # Set torso position and orientation (identity quaternion)
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
                    if j % 2 == 0:  # hip joints: swing ±0.5 rad
                        joints.append(0.5 * s)
                    else:           # ankle joints: oscillate within [-0.75, -0.2] rad
                        joints.append(-0.475 + 0.275 * s)
                self._data.qpos[start + 7:start + 15] = joints
            else:
                # Rest pose
                self._data.qpos[start + 7:start + 15] = [0, -0.4, 0, -0.4, 0, -0.4, 0, -0.4]

        mujoco.mj_forward(self._model, self._data)
        self._viewer.sync()

    def handle_exit(self):
        if self._viewer is not None:
            self._viewer.close()

    def _init_scene(self, state: SimulationState) -> None:
        self._robot_ids = list(state.robots.keys())
        env = state.environment
        xml = _build_xml(len(self._robot_ids), env.width, env.height, env.obstacles)
        self._model = mujoco.MjModel.from_xml_string(xml)
        self._data = mujoco.MjData(self._model)
        self._viewer = mujoco.viewer.launch_passive(self._model, self._data)
