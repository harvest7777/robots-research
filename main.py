"""
MuJoCo simulation view demo.

Run with:
    mjpython main.py
"""

import sys
import time

sys.path.insert(0, ".")

from simulation import (
    Environment, Robot, RobotId, RobotState,
    WorkTask, SpatialConstraint, TaskId, TaskState,
    SimulationRunner, InMemorySimulationStore, InMemoryAssignmentService,
    Assignment, astar_pathfind,
)
from simulation.primitives import Position, Time
from simulation_view.mujoco.mujoco_view_service import MujocoViewService

# --- Environment ---
env = Environment(width=10, height=10)
for pos in [
    Position(2, 2), Position(2, 3), Position(2, 4),
    Position(5, 1), Position(5, 2), Position(5, 3),
    Position(7, 6), Position(7, 7), Position(6, 7),
]:
    env.add_obstacle(pos)

# --- Robots ---
ROBOT_1 = RobotId(1)
ROBOT_2 = RobotId(2)
ROBOT_3 = RobotId(3)

robots = [
    (Robot(id=ROBOT_1, capabilities=frozenset()), RobotState(robot_id=ROBOT_1, position=Position(0, 0))),
    (Robot(id=ROBOT_2, capabilities=frozenset()), RobotState(robot_id=ROBOT_2, position=Position(9, 0))),
    (Robot(id=ROBOT_3, capabilities=frozenset()), RobotState(robot_id=ROBOT_3, position=Position(0, 9))),
]

# --- Tasks ---
TASK_1 = TaskId(1)
TASK_2 = TaskId(2)
TASK_3 = TaskId(3)

tasks = [
    (
        WorkTask(id=TASK_1, priority=5, required_work_time=Time(5),
                 spatial_constraint=SpatialConstraint(target=Position(8, 8), max_distance=0)),
        TaskState(task_id=TASK_1),
    ),
    (
        WorkTask(id=TASK_2, priority=5, required_work_time=Time(5),
                 spatial_constraint=SpatialConstraint(target=Position(4, 5), max_distance=0)),
        TaskState(task_id=TASK_2),
    ),
    (
        WorkTask(id=TASK_3, priority=5, required_work_time=Time(5),
                 spatial_constraint=SpatialConstraint(target=Position(8, 1), max_distance=0)),
        TaskState(task_id=TASK_3),
    ),
]

assignments = [
    Assignment(robot_id=ROBOT_1, task_id=TASK_1),
    Assignment(robot_id=ROBOT_2, task_id=TASK_3),
    Assignment(robot_id=ROBOT_3, task_id=TASK_2),
]

# --- Setup ---
store = InMemorySimulationStore()
for robot, state in robots:
    store.add_robot(robot, state)
for task, state in tasks:
    store.add_task(task, state)

view = MujocoViewService()
runner = SimulationRunner(
    environment=env,
    store=store,
    assignment_service=InMemoryAssignmentService(assignments),
    pathfinding=astar_pathfind,
    view_service=view,
)

# --- Run ---
try:
    for _ in range(300):
        runner.step()
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    runner.stop()
