from dataclasses import dataclass, field
import math


@dataclass
class Zone:
    name: str
    x: float
    y: float


@dataclass
class Station:
    name: str
    x: float
    y: float


@dataclass
class Environment:
    width: float
    height: float
    occupancy_grid: list[list[bool]] = field(default_factory=list)
    grid_resolution: float = 1.0
    zones: list[Zone] = field(default_factory=list)
    stations: list[Station] = field(default_factory=list)

    def __post_init__(self):
        if not self.occupancy_grid:
            rows = int(self.height / self.grid_resolution)
            cols = int(self.width / self.grid_resolution)
            self.occupancy_grid = [[False for _ in range(cols)] for _ in range(rows)]

    def _to_grid(self, x: float, y: float) -> tuple[int, int]:
        col = int(x / self.grid_resolution)
        row = int(y / self.grid_resolution)
        return row, col

    def _in_bounds(self, x: float, y: float) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def is_free(self, x: float, y: float) -> bool:
        if not self._in_bounds(x, y):
            return False
        row, col = self._to_grid(x, y)
        if row >= len(self.occupancy_grid) or col >= len(self.occupancy_grid[0]):
            return False
        return not self.occupancy_grid[row][col]

    def set_blocked(self, x: float, y: float, blocked: bool = True):
        if not self._in_bounds(x, y):
            return
        row, col = self._to_grid(x, y)
        if row < len(self.occupancy_grid) and col < len(self.occupancy_grid[0]):
            self.occupancy_grid[row][col] = blocked

    def distance(self, a: tuple[float, float], b: tuple[float, float], metric: str = "euclidean") -> float:
        if metric == "manhattan":
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def is_path_free(self, a: tuple[float, float], b: tuple[float, float], step_size: float = 0.5) -> bool:
        dist = self.distance(a, b)
        if dist == 0:
            return self.is_free(a[0], a[1])

        steps = int(dist / step_size) + 1
        for i in range(steps + 1):
            t = i / steps
            x = a[0] + t * (b[0] - a[0])
            y = a[1] + t * (b[1] - a[1])
            if not self.is_free(x, y):
                return False
        return True
