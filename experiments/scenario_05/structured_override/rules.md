# Override Rules

- SEALED REGION: The rectangular area bounded by x=6..12, y=3..5 is fully enclosed by impassable obstacles with no entrance. No robot can ever reach any position inside this region.
- IGNORE UNREACHABLE TASKS: Any task whose position falls within x=6..12, y=3..5 must never be assigned to any robot. Assigning a robot to such a task wastes it indefinitely — the robot will path-find to the wall and stall.
- ASSIGN ONLY REACHABLE TASKS: Only assign robots to tasks whose positions are outside the sealed region. Even if a sealed task has higher priority, skip it and assign robots to the next available reachable task.
