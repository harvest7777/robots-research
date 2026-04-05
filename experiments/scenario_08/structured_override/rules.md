# Override Rules

- FORMATION QUORUM: Each MoveTask requires exactly 3 robots in close proximity (within distance 1) to advance. If fewer than 3 robots are assigned to a formation, it cannot move — do not waste robots on an incomplete formation.
- SEQUENTIAL FORMATIONS: With only 5 robots and two formations each requiring 3, you cannot run both formations simultaneously. Assign 3 robots to one cargo task and complete it fully before reassigning robots to the second cargo task. The 2 remaining unassigned robots should idle or be held in reserve.
- DO NOT SPLIT EVENLY: Assigning 2 robots to each formation leaves both permanently stalled. Always ensure at least one formation has its full quorum of 3.
