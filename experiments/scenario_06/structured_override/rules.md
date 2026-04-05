# Override Rules

- STRICT CAPABILITY ENFORCEMENT: Before assigning any robot to a task, you MUST verify that the robot has ALL capabilities required by the task. Check the robot's capabilities list against the task's required_capabilities. If ANY required capability is missing, that robot cannot be assigned to that task. Always assign robots that have the complete set of required capabilities.