"""
llm/tools.py

Tool definitions and handlers for LLM-based robot assignment.

`make_tools(store, assignment_service)` returns:
  - list[dict]              — OpenAI-format tool schemas to pass to litellm
  - dict[str, Callable]     — handler map keyed by tool name; each handler
                              takes the LLM's args dict and returns a string
"""

from __future__ import annotations

import json
from typing import Callable

from langsmith import traceable

from simulation.domain.move_task import MoveTask, MoveTaskState
from simulation.domain.search_task import SearchTask, SearchTaskState
from simulation.domain.task import WorkTask
from simulation.domain.task_state import TaskState
from simulation.engine_rewrite.services.base_assignment_service import BaseAssignmentService
from simulation.engine_rewrite.services.base_simulation_store import BaseSimulationStore
from simulation.domain.assignment import Assignment
from simulation.domain.robot_state import RobotId
from simulation.domain.base_task import TaskId


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def _serialise_state(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
) -> dict:
    robot_states, task_states = store.get_snapshot()
    robots_by_id = {r.id: r for r in store.all_robots()}
    tasks_by_id = {t.id: t for t in store.all_tasks()}

    robots = []
    for robot_id, state in robot_states.items():
        robot = robots_by_id[robot_id]
        robots.append({
            "id": robot_id,
            "position": {"x": state.position.x, "y": state.position.y},
            "battery": round(state.battery_level, 3),
            "capabilities": sorted(c.name for c in robot.capabilities),
        })

    tasks = []
    for task_id, task_state in task_states.items():
        task = tasks_by_id[task_id]
        entry: dict = {
            "id": task_id,
            "priority": task.priority,
            "status": task_state.status.value if task_state.status else None,
            "required_capabilities": sorted(c.name for c in task.required_capabilities),
        }

        if isinstance(task, SearchTask):
            assert isinstance(task_state, SearchTaskState)
            entry["type"] = "search"
            entry["rescue_found"] = sorted(task_state.rescue_found)

        elif isinstance(task, MoveTask):
            assert isinstance(task_state, MoveTaskState)
            entry["type"] = "move"
            entry["current_position"] = {
                "x": task_state.current_position.x,
                "y": task_state.current_position.y,
            }
            entry["destination"] = {
                "x": task.destination.x,
                "y": task.destination.y,
            }
            entry["min_robots_required"] = task.min_robots_required

        elif isinstance(task, WorkTask):
            assert isinstance(task_state, TaskState)
            entry["type"] = "work"
            entry["work_done"] = task_state.work_done.tick
            entry["work_required"] = task.required_work_time.tick
            if task.spatial_constraint is not None:
                t = task.spatial_constraint.target
                entry["location"] = (
                    {"x": t.x, "y": t.y}
                    if hasattr(t, "x")
                    else {"zone_id": int(t)}
                )

        tasks.append(entry)

    assignments = [
        {"robot_id": a.robot_id, "task_id": a.task_id}
        for a in assignment_service.get_current()
    ]

    return {"robots": robots, "tasks": tasks, "assignments": assignments}


# ---------------------------------------------------------------------------
# Tool factory
# ---------------------------------------------------------------------------


def make_tools(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
) -> tuple[list[dict], dict[str, Callable[[dict], str]]]:
    """
    Return (schemas, handlers) for the two assignment tools.

    schemas  — OpenAI-format tool dicts, pass directly to litellm
    handlers — dispatch by tool name: handlers[name](args) -> result_str
    """

    schemas = [
        {
            "type": "function",
            "function": {
                "name": "get_state",
                "description": (
                    "Return the current simulation state: all robots (position, battery, "
                    "capabilities), all tasks (type, status, progress, location), and the "
                    "current robot-to-task assignments."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_assignments",
                "description": (
                    "Overwrite the current robot-to-task assignments. Each robot may be "
                    "assigned to at most one task. Robots omitted from the list keep their "
                    "existing assignment. Pass an empty list to clear all assignments."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "assignments": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "robot_id": {"type": "integer"},
                                    "task_id": {"type": "integer"},
                                },
                                "required": ["robot_id", "task_id"],
                            },
                            "description": "List of robot-to-task pairs to apply.",
                        }
                    },
                    "required": ["assignments"],
                },
            },
        },
    ]

    @traceable(run_type="tool", name="get_state")
    def handle_get_state(_args: dict) -> str:
        return json.dumps(_serialise_state(store, assignment_service), indent=2)

    @traceable(run_type="tool", name="write_assignments")
    def handle_write_assignments(args: dict) -> str:
        new_assignments = [
            Assignment(
                robot_id=RobotId(a["robot_id"]),
                task_id=TaskId(a["task_id"]),
            )
            for a in args["assignments"]
        ]
        assignment_service.update(new_assignments)
        pairs = ", ".join(
            f"R{a.robot_id}→T{a.task_id}" for a in new_assignments
        )
        return f"Assignments written ({len(new_assignments)}): {pairs or 'none'}"

    handlers: dict[str, Callable[[dict], str]] = {
        "get_state": handle_get_state,
        "write_assignments": handle_write_assignments,
    }

    return schemas, handlers
