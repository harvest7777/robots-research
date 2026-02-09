# SimulationView: pure, stateless renderer for a single SimulationSnapshot.
#
# Receives an immutable SimulationSnapshot and produces a Frame (2D character
# grid).  Contains NO ANSI codes, NO printing, NO terminal awareness, NO
# diffing, NO state.  Deterministic: same snapshot + same dimensions → same
# frame, always.

from simulation_models.environment import Obstacle
from simulation_models.position import Position
from simulation_models.snapshot import SimulationSnapshot
from simulation_models.task import TaskId, TaskType
from simulation_models.task_state import TaskStatus
from simulation_models.zone import ZoneId, ZoneType

from .frame import Frame, make_frame, stamp

# ---------------------------------------------------------------------------
# Symbol dictionaries
# ---------------------------------------------------------------------------

ZONE_SYMBOLS: dict[ZoneType, str] = {
    ZoneType.INSPECTION: "I",
    ZoneType.MAINTENANCE: "M",
    ZoneType.LOADING: "L",
    ZoneType.RESTRICTED: "X",
    ZoneType.CHARGING: "C",
}

TASK_STATUS_SYMBOLS: dict[TaskStatus, str] = {
    TaskStatus.UNASSIGNED: "○",
    TaskStatus.ASSIGNED: "◐",
    TaskStatus.IN_PROGRESS: "◑",
    TaskStatus.DONE: "●",
    TaskStatus.FAILED: "✗",
}

TASK_TYPE_LABELS: dict[TaskType, str] = {
    TaskType.ROUTINE_INSPECTION: "RI",
    TaskType.ANOMALY_INVESTIGATION: "AI",
    TaskType.PREVENTIVE_MAINTENANCE: "PM",
    TaskType.EMERGENCY_RESPONSE: "ER",
    TaskType.PICKUP: "PU",
}

TASK_TYPE_FULL_NAMES: dict[TaskType, str] = {
    TaskType.ROUTINE_INSPECTION: "Routine Inspection",
    TaskType.ANOMALY_INVESTIGATION: "Anomaly Investigation",
    TaskType.PREVENTIVE_MAINTENANCE: "Preventive Maintenance",
    TaskType.EMERGENCY_RESPONSE: "Emergency Response",
    TaskType.PICKUP: "Pickup",
}

ROBOT_SYMBOL = "R"
OBSTACLE_SYMBOL = "#"
TASK_AREA_SYMBOL = "+"
EMPTY_SYMBOL = "."


class SimulationView:
    def __init__(self, snapshot: SimulationSnapshot) -> None:
        self.snapshot = snapshot

    def render(self, width: int, height: int) -> Frame:
        """Build a fully populated 2D character grid from the snapshot."""
        frame = make_frame(width, height)
        row = 0

        row = self._render_header(frame, row)
        row += 1  # blank separator

        row = self._render_grid(frame, row)
        row += 1  # blank separator

        row = self._render_robots(frame, row)
        row += 1  # blank separator

        row = self._render_tasks(frame, row)
        row += 1  # blank separator

        self._render_robot_activity(frame, row)

        return frame

    # ------------------------------------------------------------------
    # Section renderers — each writes into *frame* and returns next row
    # ------------------------------------------------------------------

    def _render_header(self, frame: Frame, start_row: int) -> int:
        t = self.snapshot.t_now
        text = f"t={t.tick}" if t is not None else "t=?"
        stamp(frame, start_row, 0, text)
        return start_row + 1

    def _render_grid(self, frame: Frame, start_row: int) -> int:
        env = self.snapshot.env

        robot_positions: dict[Position, object] = {}
        for rid, state in self.snapshot.robot_states.items():
            robot_positions[state.position] = rid

        targets, areas = self._compute_task_work_areas()

        for y in range(env.height):
            frame_row = start_row + y
            if frame_row >= len(frame):
                break
            for x in range(env.width):
                pos = Position(x, y)
                if pos in robot_positions:
                    symbol = ROBOT_SYMBOL
                elif pos in env.obstacles:
                    symbol = OBSTACLE_SYMBOL
                elif pos in targets:
                    symbol = self._task_id_symbol(targets[pos])
                elif pos in areas:
                    symbol = TASK_AREA_SYMBOL
                else:
                    zone_sym = self._zone_symbol_at(pos)
                    symbol = zone_sym if zone_sym else EMPTY_SYMBOL

                frame_col = x * 2  # space-separated layout
                if frame_col < len(frame[frame_row]):
                    frame[frame_row][frame_col] = symbol

        return start_row + env.height

    def _render_robots(self, frame: Frame, start_row: int) -> int:
        row = start_row
        if row >= len(frame):
            return row
        stamp(frame, row, 0, "Robots:")
        row += 1

        for robot in self.snapshot.robots:
            if row >= len(frame):
                break
            state = self.snapshot.robot_states[robot.id]
            text = (
                f"  {ROBOT_SYMBOL} Robot {robot.id}"
                f"  pos=({state.x:.0f},{state.y:.0f})"
                f"  battery={state.battery_level:.0%}"
            )
            stamp(frame, row, 0, text)
            row += 1

        return row

    def _render_tasks(self, frame: Frame, start_row: int) -> int:
        row = start_row
        if row >= len(frame):
            return row
        stamp(frame, row, 0, "Tasks:")
        row += 1

        for task in self.snapshot.tasks:
            if row >= len(frame):
                break
            state = self.snapshot.task_states[task.id]
            status = TASK_STATUS_SYMBOLS.get(state.status, "?")
            label = TASK_TYPE_LABELS.get(task.type, "??")
            spatial = self._spatial_info(task)
            text = (
                f"  {status} [{label}] Task {task.id}"
                f"  priority={task.priority}"
                f"  progress={state.work_done.tick}/{task.required_work_time.tick}"
                f"{spatial}"
            )
            stamp(frame, row, 0, text)
            row += 1

        return row

    def _render_robot_activity(self, frame: Frame, start_row: int) -> int:
        robot_task_map: dict[object, object] = {}
        for task in self.snapshot.tasks:
            state = self.snapshot.task_states[task.id]
            if state.status in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS):
                for rid in state.assigned_robot_ids:
                    robot_task_map[rid] = task

        row = start_row
        if row >= len(frame):
            return row
        stamp(frame, row, 0, "Activity:")
        row += 1

        for robot in self.snapshot.robots:
            if row >= len(frame):
                break
            rstate = self.snapshot.robot_states[robot.id]
            task = robot_task_map.get(robot.id)
            if task is not None:
                name = TASK_TYPE_FULL_NAMES.get(task.type, "Unknown")
                tstate = self.snapshot.task_states[task.id]
                text = (
                    f"  Robot {robot.id} ({rstate.x:.0f},{rstate.y:.0f})"
                    f" is working on {name} (Task {task.id})"
                    f" ({tstate.status.value})"
                )
            else:
                text = (
                    f"  Robot {robot.id} ({rstate.x:.0f},{rstate.y:.0f})"
                    f" is idle"
                )
            stamp(frame, row, 0, text)
            row += 1

        return row

    # ------------------------------------------------------------------
    # Helpers (unchanged logic from the original)
    # ------------------------------------------------------------------

    def _compute_task_work_areas(
        self,
    ) -> tuple[dict[Position, TaskId], dict[Position, TaskId]]:
        targets: dict[Position, TaskId] = {}
        areas: dict[Position, TaskId] = {}
        env = self.snapshot.env
        for task in self.snapshot.tasks:
            state = self.snapshot.task_states[task.id]
            if state.status in (TaskStatus.DONE, TaskStatus.FAILED):
                continue
            sc = task.spatial_constraint
            if sc is None:
                continue
            if isinstance(sc.target, Position):
                targets.setdefault(sc.target, task.id)
                if sc.max_distance > 0:
                    for dy in range(-sc.max_distance, sc.max_distance + 1):
                        for dx in range(-sc.max_distance, sc.max_distance + 1):
                            if abs(dx) + abs(dy) <= sc.max_distance:
                                p = Position(sc.target.x + dx, sc.target.y + dy)
                                if p != sc.target and 0 <= p.x < env.width and 0 <= p.y < env.height:
                                    areas.setdefault(p, task.id)
            else:
                zone = env.get_zone(sc.target)
                if zone is not None:
                    for p in zone.cells:
                        areas.setdefault(p, task.id)
        return targets, areas

    @staticmethod
    def _task_id_symbol(task_id: TaskId) -> str:
        return str(int(task_id)) if int(task_id) < 10 else "*"

    def _zone_symbol_at(self, pos: Position) -> str | None:
        for zone in self.snapshot.env._zones.values():
            if zone.contains(pos):
                return ZONE_SYMBOLS.get(zone.zone_type, "?")
        return None

    @staticmethod
    def _spatial_info(task: "Task") -> str:
        sc = task.spatial_constraint
        if sc is None:
            return ""
        if isinstance(sc.target, Position):
            s = f"  at ({sc.target.x},{sc.target.y})"
            if sc.max_distance > 0:
                s += f" r={sc.max_distance}"
            return s
        return f"  zone={int(sc.target)}"
