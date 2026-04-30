# Docker New Plan

## Overview

Docker is opt-in via a `--docker` CLI flag. When enabled, one container is spun up per robot before the simulation loop starts, telemetry is forwarded each tick via `exec_run`, and all containers are stopped and removed in a `finally` block after the loop ends. When the flag is absent, the simulation runs exactly as it does today.

---

## Step 1 — Create the `docker/` package

Four files. No imports from this package touch `experiments/`.

### `docker/__init__.py`

Empty. Makes `docker` a package.

---

### `docker/service.py`

Owns the `ContainerId` type and the `DockerService` class. No simulation imports.

The container is responsible for its own logging. Each tick the simulation sends a command to the container via `exec_run`, and the container's own shell process writes the telemetry line to `/proc/1/fd/1` — PID 1's stdout file descriptor — which Docker captures as the log stream. No stdin, no sockets, no framing.

Container objects are cached at creation time so `write_log` never calls `containers.get()`.

```python
from typing import NewType, Any
import docker as docker_sdk

ContainerId = NewType("ContainerId", str)

class DockerService:
    def __init__(self) -> None:
        self._client = docker_sdk.from_env()
        self._containers: dict[ContainerId, Any] = {}

    def create_and_start(self, name: str, image: str) -> ContainerId:
        container = self._client.containers.run(
            image,
            name=name,
            detach=True,
        )
        cid = ContainerId(container.id)
        self._containers[cid] = container
        return cid

    def write_log(self, container_id: ContainerId, line: str) -> None:
        self._containers[container_id].exec_run(
            ['sh', '-c', 'printf "%s\n" "$T" >/proc/1/fd/1'],
            environment={'T': line},
        )

    def stop_and_remove(self, container_id: ContainerId) -> None:
        container = self._containers.pop(container_id)
        container.stop()
        container.remove()
```

---

### `docker/telemetry.py`

Defines `RobotAction` and `RobotTelemetry`. Imports from simulation domain only.

```python
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any

from simulation.primitives.capability import Capability
from simulation.primitives.position import Position
from simulation.primitives.time import Time
from simulation.domain.robot_state import RobotId
from simulation.domain.base_task import TaskId
from simulation.domain.step_outcome import IgnoreReason


class RobotAction(Enum):
    MOVED  = "moved"   # robot appears in outcome.moved
    WORKED = "worked"  # robot appears in outcome.worked
    STUCK  = "stuck"   # robot appears in outcome.robots_stuck
    IDLE   = "idle"    # robot appears in none of the above


@dataclass(frozen=True)
class RobotTelemetry:
    tick:                 Time
    robot_id:             RobotId
    position:             Position
    battery_level:        float
    current_waypoint:     Position | None
    action:               RobotAction
    assigned_task_ids:    tuple[TaskId, ...]
    task_capabilities:    frozenset[Capability]   # serialized with sorted() for determinism
    task_complexity:      int | None              # WorkTask.required_work_time.tick, else None
    deadline_delta_ticks: int | None              # deadline.tick - t_now.tick; negative = overdue; None = no deadline
    ignore_reasons:       tuple[IgnoreReason, ...]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "tick":                 self.tick.tick,
            "robot_id":             int(self.robot_id),
            "position":             {"x": self.position.x, "y": self.position.y},
            "battery_level":        self.battery_level,
            "current_waypoint":     (
                {"x": self.current_waypoint.x, "y": self.current_waypoint.y}
                if self.current_waypoint is not None else None
            ),
            "action":               self.action.value,
            "assigned_task_ids":    [int(t) for t in self.assigned_task_ids],
            "task_capabilities":    sorted(c.value for c in self.task_capabilities),
            "task_complexity":      self.task_complexity,
            "deadline_delta_ticks": self.deadline_delta_ticks,
            "ignore_reasons":       [r.value for r in self.ignore_reasons],
        }
```

---

### `docker/adapter.py`

Pure function. Takes one robot's slice of `SimulationState` and `StepOutcome` and returns a `RobotTelemetry`. No Docker SDK imports.

```python
from simulation.domain.robot_state import RobotId
from simulation.domain.simulation_state import SimulationState
from simulation.domain.step_outcome import StepOutcome
from simulation.domain.task import WorkTask
from docker.telemetry import RobotAction, RobotTelemetry


def build_telemetry(
    robot_id: RobotId,
    state: SimulationState,
    outcome: StepOutcome,
) -> RobotTelemetry:
    robot_state = state.robot_states[robot_id]

    # Derive action from outcome
    moved_ids  = {r for r, _ in outcome.moved}
    worked_ids = {r for r, _ in outcome.worked}
    if robot_id in outcome.robots_stuck:
        action = RobotAction.STUCK
    elif robot_id in worked_ids:
        action = RobotAction.WORKED
    elif robot_id in moved_ids:
        action = RobotAction.MOVED
    else:
        action = RobotAction.IDLE

    assigned_task_ids = tuple(
        a.task_id for a in state.assignments if a.robot_id == robot_id
    )

    # Union of capabilities across all assigned tasks
    task_capabilities = frozenset(
        cap
        for task_id in assigned_task_ids
        if (task := state.tasks.get(task_id)) is not None
        for cap in task.required_capabilities
    )

    # WorkTask-specific fields — use first assigned WorkTask found
    task_complexity: int | None = None
    deadline_delta_ticks: int | None = None
    for task_id in assigned_task_ids:
        task = state.tasks.get(task_id)
        if isinstance(task, WorkTask):
            task_complexity = task.required_work_time.tick
            if task.deadline is not None:
                deadline_delta_ticks = task.deadline.tick - state.t_now.tick
            break

    ignore_reasons = tuple(
        reason
        for assignment, reason in outcome.assignments_ignored
        if assignment.robot_id == robot_id
    )

    return RobotTelemetry(
        tick=state.t_now,
        robot_id=robot_id,
        position=robot_state.position,
        battery_level=robot_state.battery_level,
        current_waypoint=robot_state.current_waypoint,
        action=action,
        assigned_task_ids=assigned_task_ids,
        task_capabilities=task_capabilities,
        task_complexity=task_complexity,
        deadline_delta_ticks=deadline_delta_ticks,
        ignore_reasons=ignore_reasons,
    )
```

---

## Step 2 — Create the Dockerfile

Lives at `docker/Dockerfile`. PID 1 is `sleep infinity` — its only job is to keep the container alive and own the stdout file descriptor that Docker watches. Log lines are written to `/proc/1/fd/1` by exec'd processes, not by PID 1 itself.

```dockerfile
FROM alpine:3.19
CMD ["sleep", "infinity"]
```

Build command (run once):
```bash
docker build -t robot-telemetry:latest -f docker/Dockerfile .
```

---

## Step 3 — Add `docker` field to `Run`

In `experiments/swag_runner/models.py`, add an opt-in flag:

```python
@dataclass(frozen=True)
class Run:
    scenario: str
    override_type: Override
    model: str
    docker: bool = False
```

---

## Step 4 — Modify `experiments/swag_runner/run.py`

Three small, additive changes. No existing behaviour changes when `--docker` is not passed.

### 4a — Add `--docker` to `_parse_arguments()`

```python
parser.add_argument("--docker", action="store_true", default=False)
```

Pass it through to `Run`:

```python
return Run(
    scenario=scenario,
    override_type=Override(override_variant),
    model=model,
    docker=args.docker,
)
```

### 4b — Modify `_run_loop` to accept optional Docker params

```python
def _run_loop(
    runner: SimulationRunner,
    agent: AssignmentAgent,
    store: BaseSimulationStore,
    tasks_to_spawn: list[SpawnTask],
    docker_service: DockerService | None = None,
    containers: dict[RobotId, ContainerId] | None = None,
) -> None:
    ...
    for _ in range(MAX_TICKS):
        ...
        state, outcome = runner.step()   # was: _, outcome = runner.step()

        if docker_service is not None and containers is not None:
            for robot_id in state.robot_states:
                telemetry = build_telemetry(robot_id, state, outcome)
                docker_service.write_log(
                    containers[robot_id],
                    json.dumps(telemetry.to_json_dict()),
                )

        should_reassign = ...
```

### 4c — Add container lifecycle in `run()`

Wrap the `_run_loop` call in a dedicated `try/finally` for Docker cleanup, nested inside the existing `shutil.rmtree` handler:

```python
docker_service = DockerService() if run_params.docker else None
containers: dict[RobotId, ContainerId] = {}

try:
    if docker_service is not None:
        for robot in store.all_robots():
            containers[robot.id] = docker_service.create_and_start(
                name=f"robot-{robot.id}",
                image="robot-telemetry:latest",
            )
    try:
        _run_loop(runner, agent, store, task_spawns, docker_service, containers)
    except:
        shutil.rmtree(run_dir)
        raise
finally:
    for cid in containers.values():
        docker_service.stop_and_remove(cid)
```

---

## File Summary

| File | Action |
|---|---|
| `docker/__init__.py` | Create |
| `docker/service.py` | Create |
| `docker/telemetry.py` | Create |
| `docker/adapter.py` | Create |
| `docker/Dockerfile` | Create |
| `experiments/swag_runner/models.py` | Add `docker: bool = False` to `Run` |
| `experiments/swag_runner/run.py` | Add `--docker` flag, modify `_run_loop`, add container lifecycle |
| `requirements.txt` | Already updated — `docker>=7.0.0` |
