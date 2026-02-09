# SimulationView: stateless renderer for a single SimulationSnapshot.
#
# Receives an immutable SimulationSnapshot and produces a visual
# representation of that moment in time. Owns no simulation state —
# all data comes from the snapshot. This keeps rendering fully
# decoupled from the live Simulation and makes any snapshot in the
# history dict renderable with no extra setup.

from simulation_models.environment import Obstacle
from simulation_models.position import Position
from simulation_models.snapshot import SimulationSnapshot
from simulation_models.task import TaskType
from simulation_models.task_state import TaskStatus
from simulation_models.zone import ZoneType

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
EMPTY_SYMBOL = "."


class SimulationView:
    def __init__(self, snapshot: SimulationSnapshot) -> None:
        self.snapshot = snapshot

    def render(self) -> str:
        parts = [
            self._render_header(),
            self._render_grid(),
            self._render_robots(),
            self._render_tasks(),
            self._render_robot_activity(),
        ]
        return "\n\n".join(parts)

    def _render_header(self) -> str:
        t = self.snapshot.t_now
        return f"t={t.tick}" if t is not None else "t=?"

    def _render_grid(self) -> str:
        env = self.snapshot.env
        robot_positions: dict[Position, object] = {}
        for rid, state in self.snapshot.robot_states.items():
            robot_positions[state.position] = rid

        rows: list[str] = []
        for y in range(env.height):
            row: list[str] = []
            for x in range(env.width):
                pos = Position(x, y)
                if pos in robot_positions:
                    row.append(ROBOT_SYMBOL)
                elif pos in env.obstacles:
                    row.append(OBSTACLE_SYMBOL)
                else:
                    zone_sym = self._zone_symbol_at(pos)
                    row.append(zone_sym if zone_sym else EMPTY_SYMBOL)
            rows.append(" ".join(row))
        return "\n".join(rows)

    def _zone_symbol_at(self, pos: Position) -> str | None:
        # Access internal _zones; a public accessor on Environment can be added later.
        for zone in self.snapshot.env._zones.values():
            if zone.contains(pos):
                return ZONE_SYMBOLS.get(zone.zone_type, "?")
        return None

    def _render_robots(self) -> str:
        lines = ["Robots:"]
        for robot in self.snapshot.robots:
            state = self.snapshot.robot_states[robot.id]
            lines.append(
                f"  {ROBOT_SYMBOL} Robot {robot.id}"
                f"  pos=({state.x:.0f},{state.y:.0f})"
                f"  battery={state.battery_level:.0%}"
            )
        return "\n".join(lines)

    def _render_tasks(self) -> str:
        lines = ["Tasks:"]
        for task in self.snapshot.tasks:
            state = self.snapshot.task_states[task.id]
            status = TASK_STATUS_SYMBOLS.get(state.status, "?")
            label = TASK_TYPE_LABELS.get(task.type, "??")
            lines.append(
                f"  {status} [{label}] Task {task.id}"
                f"  priority={task.priority}"
                f"  progress={state.work_done.tick}/{task.required_work_time.tick}"
            )
        return "\n".join(lines)

    def _render_robot_activity(self) -> str:
        # Build reverse mapping: robot_id -> task
        robot_task_map: dict[object, object] = {}
        for task in self.snapshot.tasks:
            state = self.snapshot.task_states[task.id]
            if state.status in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS):
                for rid in state.assigned_robot_ids:
                    robot_task_map[rid] = task

        lines = ["Activity:"]
        for robot in self.snapshot.robots:
            rstate = self.snapshot.robot_states[robot.id]
            task = robot_task_map.get(robot.id)
            if task is not None:
                name = TASK_TYPE_FULL_NAMES.get(task.type, "Unknown")
                tstate = self.snapshot.task_states[task.id]
                lines.append(
                    f"  Robot {robot.id} ({rstate.x:.0f},{rstate.y:.0f})"
                    f" is working on {name} (Task {task.id})"
                    f" ({tstate.status.value})"
                )
            else:
                lines.append(
                    f"  Robot {robot.id} ({rstate.x:.0f},{rstate.y:.0f})"
                    f" is idle"
                )
        return "\n".join(lines)
