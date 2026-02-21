import json

import pytest
from fastmcp import Client

from mcp_server.server import mcp
from mcp_server.sim_state import _build_default_scenario, _live_sim


@pytest.fixture(autouse=True)
def reset_live_sim():
    """Reset the live sim to a fresh scenario before each test."""
    import mcp_server.sim_state as sim_state_mod

    fresh = _build_default_scenario()
    sim_state_mod._live_sim = fresh
    yield
    # restore original reference so nothing leaks between test files
    sim_state_mod._live_sim = _live_sim


@pytest.fixture
async def client():
    async with Client(mcp) as c:
        yield c


# ---------------------------------------------------------------------------
# Existing tools
# ---------------------------------------------------------------------------


async def test_ping(client):
    result = await client.call_tool("ping", {})
    assert result.content[0].text == "pong"


async def test_hello(client):
    result = await client.call_tool("hello", {"name": "world"})
    assert result.content[0].text == "Hello, world!"


async def test_tools_are_listed(client):
    tools = await client.list_tools()
    names = [t.name for t in tools]
    assert "ping" in names
    assert "hello" in names


# ---------------------------------------------------------------------------
# get_state
# ---------------------------------------------------------------------------


async def test_get_state_returns_valid_json(client):
    result = await client.call_tool("get_state", {})
    state = json.loads(result.content[0].text)
    assert "t" in state
    assert "environment" in state
    assert "robots" in state
    assert "tasks" in state


async def test_get_state_has_correct_structure(client):
    result = await client.call_tool("get_state", {})
    state = json.loads(result.content[0].text)

    assert state["t"] == 0
    assert state["environment"]["width"] == 12
    assert state["environment"]["height"] == 12

    assert len(state["robots"]) == 3
    for robot in state["robots"]:
        assert "id" in robot
        assert "capabilities" in robot
        assert "x" in robot
        assert "y" in robot
        assert "battery" in robot
        assert robot["battery"] == pytest.approx(1.0)

    assert len(state["tasks"]) == 2
    for task in state["tasks"]:
        assert "id" in task
        assert "type" in task
        assert "status" in task
        assert task["status"] == "unassigned"
        assert "target" in task


async def test_get_state_tools_listed(client):
    tools = await client.list_tools()
    names = [t.name for t in tools]
    assert "get_state" in names


# ---------------------------------------------------------------------------
# evaluate_assignment
# ---------------------------------------------------------------------------


async def test_evaluate_assignment_returns_valid_json(client):
    assignments = json.dumps([{"task_id": 1, "robot_ids": [2]}])
    result = await client.call_tool(
        "evaluate_assignment", {"assignments": assignments, "ticks": 10}
    )
    data = json.loads(result.content[0].text)
    assert "ticks_elapsed" in data
    assert "all_tasks_completed" in data
    assert "task_outcomes" in data
    assert "robot_outcomes" in data


async def test_evaluate_assignment_does_not_mutate_live_sim(client):
    # Record live sim state before evaluation
    before = json.loads((await client.call_tool("get_state", {})).content[0].text)

    assignments = json.dumps([{"task_id": 1, "robot_ids": [1]}, {"task_id": 2, "robot_ids": [3]}])
    await client.call_tool("evaluate_assignment", {"assignments": assignments, "ticks": 30})

    # Live sim should be unchanged
    after = json.loads((await client.call_tool("get_state", {})).content[0].text)
    assert before["t"] == after["t"]
    for r_before, r_after in zip(before["robots"], after["robots"]):
        assert r_before["x"] == r_after["x"]
        assert r_before["y"] == r_after["y"]
        assert r_before["battery"] == r_after["battery"]


async def test_evaluate_assignment_sufficient_ticks_completes_task(client):
    # Robot 1 has MANIPULATION + VISION, task 1 (PICKUP) needs MANIPULATION
    # and is at (9,9). Starting at (0,0), needs to travel ~12 cells + work 20 ticks.
    # 100 ticks should be enough.
    assignments = json.dumps([{"task_id": 1, "robot_ids": [1]}])
    result = await client.call_tool(
        "evaluate_assignment", {"assignments": assignments, "ticks": 100}
    )
    data = json.loads(result.content[0].text)
    task1 = next(o for o in data["task_outcomes"] if o["task_id"] == 1)
    assert task1["status"] == "done"
    assert task1["completed_at_tick"] is not None


async def test_evaluate_assignment_reports_battery_used(client):
    assignments = json.dumps([{"task_id": 1, "robot_ids": [2]}])
    result = await client.call_tool(
        "evaluate_assignment", {"assignments": assignments, "ticks": 20}
    )
    data = json.loads(result.content[0].text)
    robot2 = next(o for o in data["robot_outcomes"] if o["robot_id"] == 2)
    assert robot2["battery_used"] > 0
    assert robot2["battery_remaining"] < 1.0


# ---------------------------------------------------------------------------
# override_assignment
# ---------------------------------------------------------------------------


async def test_override_assignment_returns_confirmation(client):
    assignments = json.dumps([{"task_id": 1, "robot_ids": [2, 3]}])
    result = await client.call_tool("override_assignment", {"assignments": assignments})
    text = result.content[0].text
    assert "1 assignment" in text
    assert "task 1" in text


async def test_override_assignment_takes_effect_after_step(client):
    # Override: robot 2 on task 1
    assignments = json.dumps([{"task_id": 1, "robot_ids": [2]}])
    await client.call_tool("override_assignment", {"assignments": assignments})

    # Step the sim forward enough for the assignment to register
    await client.call_tool("step_simulation", {"ticks": 1})

    state = json.loads((await client.call_tool("get_state", {})).content[0].text)
    task1 = next(t for t in state["tasks"] if t["id"] == 1)
    assert task1["status"] in ("assigned", "in_progress")
    assert 2 in task1["assigned_robot_ids"]


# ---------------------------------------------------------------------------
# step_simulation
# ---------------------------------------------------------------------------


async def test_step_simulation_advances_time(client):
    await client.call_tool("step_simulation", {"ticks": 5})
    state = json.loads((await client.call_tool("get_state", {})).content[0].text)
    assert state["t"] == 5


async def test_step_simulation_default_one_tick(client):
    await client.call_tool("step_simulation", {})
    state = json.loads((await client.call_tool("get_state", {})).content[0].text)
    assert state["t"] == 1


async def test_step_simulation_returns_task_summary(client):
    result = await client.call_tool("step_simulation", {"ticks": 3})
    text = result.content[0].text
    assert "t=3" in text
    assert "task 1" in text
    assert "task 2" in text
