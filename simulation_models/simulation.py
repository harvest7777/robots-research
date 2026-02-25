"""
Simulation State Container

The Simulation class holds all state and data needed to run a simulation:
- Environment (grid, zones, obstacles)
- Robots (immutable definitions)
- Tasks (immutable definitions)
- Robot states (mutable, keyed by robot_id)
- Task states (mutable, keyed by task_id)
- Assignment algorithm (configurable by researchers)
- Time tracking (t_now, dt) and snapshot history
"""

from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from types import MappingProxyType

from simulation_models.assignment import Assignment, RobotId
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.simulation_result import SimulationResult
from simulation_models.snapshot import SimulationSnapshot
from simulation_models.task import SpatialConstraint, Task, TaskId
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time
from simulation_models.zone import ZoneId

AssignmentAlgorithm = Callable[[list[Task], list[Robot]], list[Assignment]]
"""A function that assigns robots to tasks."""

PathfindingAlgorithm = Callable[
    [Environment, Position, Position, frozenset[Position]],
    Position | None,
]
"""(environment, start, goal, occupied_by_other_robots) -> next_step or None."""

# Goal-reached epsilon: within half a cell counts as "at goal"
_AT_GOAL_EPS = 0.5


@dataclass
class Simulation:
    """
    Central container for simulation state and data.

    Data fields are required at construction. The assignment_algorithm is optional
    at construction but required before calling step().

    Attributes:
        environment: The grid environment with zones and obstacles.
        robots: List of robot definitions (immutable).
        tasks: List of task definitions (immutable).
        robot_states: Mutable state for each robot, keyed by robot_id.
        task_states: Mutable state for each task, keyed by task_id.
        assignment_algorithm: Algorithm that assigns robots to tasks. Optional at
            construction, but required before stepping.
        current_assignments: Assignments from the most recent step() call.
        t_now: Current simulation time.
        dt: Time step size per step() call.
        history: Snapshot history keyed by simulation time.
    """

    environment: Environment
    robots: list[Robot]
    tasks: list[Task]
    robot_states: dict[RobotId, RobotState]
    task_states: dict[TaskId, TaskState]
    assignment_algorithm: AssignmentAlgorithm | None = None
    pathfinding_algorithm: PathfindingAlgorithm | None = None
    current_assignments: list[Assignment] = field(default_factory=list)
    t_now: Time = field(default_factory=lambda: Time(0))
    dt: Time = field(default_factory=lambda: Time(1))
    history: dict[Time, SimulationSnapshot] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.environment is None:
            raise ValueError("Simulation requires 'environment'")
        if self.robots is None:
            raise ValueError("Simulation requires 'robots'")
        if self.tasks is None:
            raise ValueError("Simulation requires 'tasks'")
        if self.robot_states is None:
            raise ValueError("Simulation requires 'robot_states'")
        if self.task_states is None:
            raise ValueError("Simulation requires 'task_states'")

        # Build lookups for immutable robot/task lists
        self._robot_by_id: dict[RobotId, Robot] = {r.id: r for r in self.robots}
        self._task_by_id: dict[TaskId, Task] = {t.id: t for t in self.tasks}

        # Record initial snapshot at t_now=0
        self.history[self.t_now] = self.snapshot()

    def _validate_ready(self) -> None:
        """Validate that simulation is ready to step.

        Raises:
            ValueError: If assignment_algorithm or pathfinding_algorithm is not set.
        """
        if self.assignment_algorithm is None:
            raise ValueError(
                "Simulation requires 'assignment_algorithm' before stepping"
            )
        if self.pathfinding_algorithm is None:
            raise ValueError(
                "Simulation requires 'pathfinding_algorithm' before stepping"
            )

    def run(self, max_steps: int) -> SimulationResult:
        """Run the simulation to completion or until the step limit is reached.

        Terminates when all tasks are in a terminal state (DONE or FAILED) or
        when t_now reaches max_steps, whichever comes first.

        Args:
            max_steps: Maximum number of steps before the run is forced to end.

        Returns:
            SimulationResult with outcome metrics and the full snapshot history.
        """
        self._validate_ready()

        terminal = {TaskStatus.DONE, TaskStatus.FAILED}

        while int(self.t_now) < max_steps:
            if all(s.status in terminal for s in self.task_states.values()):
                break
            self._step()

        all_terminal = all(s.status in terminal for s in self.task_states.values())
        tasks_succeeded = sum(
            1 for s in self.task_states.values() if s.status == TaskStatus.DONE
        )

        return SimulationResult(
            completed=all_terminal,
            tasks_succeeded=tasks_succeeded,
            tasks_total=len(self.tasks),
            makespan=int(self.t_now) if all_terminal else None,
            snapshots=list(self.history.values()),
        )

    def _step(self) -> None:
        """Execute one simulation tick.

        Two-phase approach to prevent move-order bias:

        Plan phase: compute next positions for all robots before moving any.
        Execute phase: move robots, apply work, update task states.
        """

        # Advance simulation time
        self.t_now = self.t_now.advance(self.dt)

        # Run assignment algorithm
        self.current_assignments = self.assignment_algorithm(self.tasks, self.robots)

        robot_assignment: dict[RobotId, TaskId] = {}
        for assignment in self.current_assignments:
            for robot_id in assignment.robot_ids:
                robot_assignment[robot_id] = assignment.task_id

        # Update task assignment states
        for task in self.tasks:
            task_state = self.task_states[task.id]
            assigned_robot_ids = {
                robot_id
                for robot_id, task_id in robot_assignment.items()
                if task_id == task.id
            }
            task.set_assignment(task_state, assigned_robot_ids)

        # --- Plan phase ---
        all_positions = {
            robot_id: state.position
            for robot_id, state in self.robot_states.items()
        }
        planned_moves: dict[RobotId, Position | None] = {}

        for robot_id, state in self.robot_states.items():
            if robot_id not in robot_assignment:
                planned_moves[robot_id] = None
                continue

            task_id = robot_assignment[robot_id]
            task = self._task_by_id[task_id]
            task_state = self.task_states[task_id]

            if task_state.status in (TaskStatus.DONE, TaskStatus.FAILED):
                planned_moves[robot_id] = None
                continue

            goal = self._resolve_task_target_position(task, state.position)
            if goal is None:
                # No spatial constraint — robot works in place
                planned_moves[robot_id] = None
                continue

            if state.position.near(goal, eps=_AT_GOAL_EPS):
                planned_moves[robot_id] = None
                continue

            occupied = frozenset(
                pos
                for other_robot_id, pos in all_positions.items()
                if other_robot_id != robot_id
            )
            next_step = self.pathfinding_algorithm(
                self.environment, state.position, goal, occupied
            )
            planned_moves[robot_id] = next_step

        # Detect planned collisions using pairwise radius-based distance check.
        # Build list of (robot_id, planned_position) for robots that have a move.
        moving_robots: list[tuple[RobotId, Position]] = [
            (rid, pos)
            for rid, pos in planned_moves.items()
            if pos is not None
        ]
        for i in range(len(moving_robots)):
            rid_a, pos_a = moving_robots[i]
            if planned_moves[rid_a] is None:
                continue
            robot_a = self._robot_by_id[rid_a]
            for j in range(i + 1, len(moving_robots)):
                rid_b, pos_b = moving_robots[j]
                if planned_moves[rid_b] is None:
                    continue
                robot_b = self._robot_by_id[rid_b]
                dist = pos_a.distance(pos_b)
                if dist < robot_a.radius + robot_b.radius:
                    # Block the second robot
                    planned_moves[rid_b] = None

        # --- Execute phase ---
        obstacles = self.environment.obstacles
        for robot_id, state in self.robot_states.items():
            robot = self._robot_by_id[robot_id]
            next_pos = planned_moves.get(robot_id)

            if robot_id not in robot_assignment:
                robot.idle(state, self.dt)
                continue

            task_id = robot_assignment[robot_id]
            task = self._task_by_id[task_id]
            task_state = self.task_states[task_id]

            if task_state.status in (TaskStatus.DONE, TaskStatus.FAILED):
                robot.idle(state, self.dt)
                continue

            goal = self._resolve_task_target_position(task, state.position)

            if next_pos is not None:
                # Robot has a move to make
                robot.move_towards(state, next_pos, self.dt)
                # Layer 2: push robot out of any obstacle AABBs it may clip
                self._push_out_of_obstacles(state, robot.radius, obstacles)
            elif goal is None or state.position.near(goal, eps=_AT_GOAL_EPS):
                # At goal or no spatial constraint — do work
                robot.work(state, self.dt)
                task.apply_work(task_state, self.dt, self.t_now)
            else:
                # Stuck (pathfinding returned None, or collision-blocked)
                robot.idle(state, self.dt)

        # Record snapshot at new time
        self.history[self.t_now] = self.snapshot()

    @staticmethod
    def _push_out_of_obstacles(
        state: RobotState,
        radius: float,
        obstacles: frozenset[Position],
    ) -> None:
        """Layer 2 safety: push robot center out of any obstacle AABB it overlaps.

        Checks only the 9 cells surrounding the robot's current cell for performance.
        Each obstacle occupies the unit square [cx, cx+1] × [cy, cy+1].
        """
        cx = int(state.position.x)
        cy = int(state.position.y)
        for dox in range(-1, 2):
            for doy in range(-1, 2):
                cell = Position(float(cx + dox), float(cy + doy))
                if cell not in obstacles:
                    continue
                ox = float(cx + dox)
                oy = float(cy + doy)
                # Nearest point on AABB [ox, ox+1] × [oy, oy+1] to robot center
                nearest_x = max(ox, min(state.position.x, ox + 1.0))
                nearest_y = max(oy, min(state.position.y, oy + 1.0))
                dx = state.position.x - nearest_x
                dy = state.position.y - nearest_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < radius:
                    if dist > 1e-9:
                        # Push robot to AABB surface along penetration vector
                        scale = radius / dist
                        state.position = Position(
                            nearest_x + dx * scale,
                            nearest_y + dy * scale,
                        )
                    else:
                        # Robot center is inside obstacle — push upward
                        state.position = Position(state.position.x, oy - radius)

    def _resolve_task_target_position(self, task: Task, robot_pos: Position) -> Position | None:
        """Resolve a task's spatial constraint to a concrete Position.

        Returns:
            The target Position, or None if the task has no spatial constraint.
        """
        sc = task.spatial_constraint
        if sc is None:
            return None

        if isinstance(sc.target, Position):
            return sc.target

        # ZoneId — find nearest zone cell to the robot
        zone = self.environment.get_zone(sc.target)
        if zone is None:
            return None

        return min(
            zone.cells,
            key=lambda cell: abs(cell.x - robot_pos.x) + abs(cell.y - robot_pos.y),
        )

    def snapshot(self) -> SimulationSnapshot:
        """
        Create a read-only snapshot of current simulation state.

        The snapshot contains copies of all mutable state, so modifications to
        the returned snapshot will not affect the live simulation.

        Returns:
            SimulationSnapshot with copied state data wrapped in immutable views.
        """
        # Copy robot states (shallow copy is sufficient; fields are primitives)
        robot_states_copy = {
            rid: dataclasses.replace(state)
            for rid, state in self.robot_states.items()
        }

        # Copy task states (must copy the mutable assigned_robot_ids set)
        task_states_copy = {
            tid: TaskState(
                task_id=state.task_id,
                status=state.status,
                assigned_robot_ids=set(state.assigned_robot_ids),
                work_done=state.work_done,
                started_at=state.started_at,
                completed_at=state.completed_at,
            )
            for tid, state in self.task_states.items()
        }

        return SimulationSnapshot(
            env=self.environment,
            robots=tuple(self.robots),
            robot_states=MappingProxyType(robot_states_copy),
            tasks=tuple(self.tasks),
            task_states=MappingProxyType(task_states_copy),
            t_now=self.t_now,
        )
