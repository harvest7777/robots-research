import sys
from dataclasses import dataclass, field

from .simulation import Simulation
from .robot import RobotStatus
from .task import TaskStatus

# ANSI escape codes
CURSOR_HOME = "\033[H"
CLEAR_SCREEN = "\033[2J"
CLEAR_LINE = "\033[K"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
YELLOW = "\033[33m"
RESET = "\033[0m"


@dataclass
class SimulationView:
    simulation: Simulation
    cell_width: int = 2
    _initialized: bool = field(default=False, repr=False)

    def init_display(self):
        """Clear screen and hide cursor once at start."""
        sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN + CURSOR_HOME)
        sys.stdout.flush()
        self._initialized = True

    def cleanup_display(self):
        """Show cursor again at end."""
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()

    def render(self, header: str = "", scale: int = 10):
        """Render frame in place without flicker."""
        if not self._initialized:
            self.init_display()

        output = CURSOR_HOME
        if header:
            output += header + "\n\n"
        output += self.get_current_view(scale=scale)
        sys.stdout.write(output)
        sys.stdout.flush()

    def icon_key_lines(self) -> list[str]:
        return [
            "Icon Key:",
            f"  R0-R9 = Robots ({YELLOW}yellow{RESET}=working)",
            "  .     = Free cell",
            "  #     = Blocked",
            "  ?     = Unassigned task",
            "  *     = Active task",
            "  +     = Completed task",
        ]

    def icon_key(self) -> str:
        return "\n".join(self.icon_key_lines())

    def get_current_view(self, scale: int = 5, show_legend: bool = True) -> str:
        sim = self.simulation
        env = sim.env

        grid_w = int(env.width // scale)
        grid_h = int(env.height // scale)

        grid = [[self._get_cell_char(x * scale, y * scale, scale) for x in range(grid_w)] for y in range(grid_h)]

        # Place tasks
        task_map = {t.id: t for t in sim.tasks}
        for task in sim.tasks:
            gx, gy = int(task.x // scale), int(task.y // scale)
            if 0 <= gx < grid_w and 0 <= gy < grid_h:
                if task.status == TaskStatus.UNASSIGNED:
                    grid[gy][gx] = "?"
                elif task.status in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS):
                    grid[gy][gx] = "*"
                elif task.status == TaskStatus.DONE:
                    grid[gy][gx] = "+"

        # Place robots (overwrite tasks if on same cell)
        for i, robot in enumerate(sim.robots):
            gx, gy = int(robot.x // scale), int(robot.y // scale)
            if 0 <= gx < grid_w and 0 <= gy < grid_h:
                label = f"R{i}"
                if robot.status in (RobotStatus.MOVING, RobotStatus.EXECUTING):
                    label = f"{YELLOW}{label}{RESET}"
                grid[gy][gx] = label

        # Build output
        grid_lines = []
        grid_lines.append("+" + "-" * (grid_w * self.cell_width) + "+")
        for row in grid:
            row_str = "|" + "".join(self._center_cell(cell) for cell in row) + "|"
            grid_lines.append(row_str)
        grid_lines.append("+" + "-" * (grid_w * self.cell_width) + "+")

        # Add legend to the right if requested
        if show_legend:
            legend = self.icon_key_lines()
            legend.insert(0, "")  # spacer
            output_lines = []
            output_lines.append(f"t={sim.t_now:.1f}s | Tasks: {self._task_summary()}")
            for i, grid_line in enumerate(grid_lines):
                legend_part = legend[i] if i < len(legend) else ""
                output_lines.append(f"{grid_line}  {legend_part}")
            output_lines.append(self._robot_status_line())
        else:
            output_lines = [f"t={sim.t_now:.1f}s | Tasks: {self._task_summary()}"]
            output_lines.extend(grid_lines)
            output_lines.append(self._robot_status_line())

        # Clear to end of each line to remove trailing artifacts
        return (CLEAR_LINE + "\n").join(output_lines) + CLEAR_LINE

    def _get_cell_char(self, x: float, y: float, scale: int) -> str:
        env = self.simulation.env
        # Check if any cell in this scaled region is blocked
        for dx in range(scale):
            for dy in range(scale):
                if not env.is_free(x + dx, y + dy):
                    return "#"
        return "."

    def _task_summary(self) -> str:
        tasks = self.simulation.tasks
        done = sum(1 for t in tasks if t.status == TaskStatus.DONE)
        in_progress = sum(1 for t in tasks if t.status in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS))
        unassigned = sum(1 for t in tasks if t.status == TaskStatus.UNASSIGNED)
        return f"{done} done, {in_progress} active, {unassigned} pending"

    def _center_cell(self, text: str) -> str:
        """Center text in cell, accounting for ANSI codes."""
        # Strip ANSI codes to get visible length
        visible = text
        for code in [YELLOW, RESET]:
            visible = visible.replace(code, "")
        padding = self.cell_width - len(visible)
        left = padding // 2
        right = padding - left
        return " " * left + text + " " * right

    def _robot_status_line(self) -> str:
        parts = []
        for i, robot in enumerate(self.simulation.robots):
            status_char = {
                RobotStatus.IDLE: "idle",
                RobotStatus.MOVING: "moving",
                RobotStatus.EXECUTING: "working",
            }.get(robot.status, "?")
            parts.append(f"R{i}:{status_char}")
        return " | ".join(parts)
