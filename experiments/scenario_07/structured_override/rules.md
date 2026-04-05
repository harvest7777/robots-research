# Override Rules

- BOTTLENECK LIMIT: The entrance area at positions (8,7), (9,7), (10,7) is a narrow bottleneck. Only 2 robots may be assigned to tasks inside the box (x >= 9) at any given time. If more than 2 robots attempt to enter, assign only 2 and wait for them to complete before assigning more. This prevents robots from blocking each other in the confined space.