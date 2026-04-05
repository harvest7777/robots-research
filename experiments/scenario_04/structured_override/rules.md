# Override Rules

- SEARCH-AND-RESCUE PRIORITY: When a SearchTask with priority 10 is present, immediately reassign as many robots as needed to that SearchTask. Do not wait for ongoing lower-priority tasks to finish first — drop them.
- MINIMIZE TIME-TO-RESCUE: The goal is to find the rescue point and complete the rescue task as fast as possible. Assign more robots to searching to reduce discovery time, even if that means leaving regular tasks incomplete or unstarted.
- RESCUE BEFORE ROUTINE: Once the rescue WorkTask spawns (after discovery), immediately assign all available robots to it. Completing the rescue takes absolute precedence over any priority-1 tasks.
