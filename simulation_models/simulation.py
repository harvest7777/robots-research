"""
what dioes a simulation ataully define then
when you run a simulation, you should at minimum, 
have an environment
a robot
some tasks to complete
and a function that assigns tasks

am i missing something here?
"""

from __future__ import annotations

import random

from simulation_models.assignment import RobotId
from simulation_models.robot_state import RobotState


"""
before all this i need the laders
how woudl thei simulatin work?
essentially on every tick you woldo do this:
run yoru assignment algorithm based on curent states
assign the tasks and robots
perform work between a robot and task which should tbh be a function of the simulation class since that is a resonsibility of the simualtion
--> but wait, how do we know if a task can be worked on?
we should get a set of all tasks that can be worked on right now.
the simulation is the main mutator
breaking this down into tasks

load the robots and their current states
data structures: 
environment: environment with the defined zones
list: robots
list: tasks 
hashmap: robot id to states
hashmap: task id to statse
"""

if __name__ == "__main__":
    state = RobotState(
        robot_id=RobotId(1),
        x=random.uniform(0, 10),
        y=random.uniform(0, 10),
        battery_level=random.uniform(0.2, 1.0),
    )
    print(state)