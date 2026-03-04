y awesome so nwo our new contract has been refactored as follows

[THIS IS ALREADY DONE]
clear everythign up

- we need to refactor the Assignment type to also have a assign_at field of type Time
- we need to refactor our Simulation to re-assign tasks based on the simluation's current time, robot and task last assigned_at time, at the assignment's assign_at time. I have left comments for this
- these things will be broken in their current state:
  simple assign doesnt have any knowledge of time

\/ i think this can be worried about later, having one assignment for main is actually fien right now, we can go off this singular assignment and have the llm build off of it which will hlep us test the "reassignment" part

- in main, we call simple assign only onc so the assignments never really actually changeo

[ALLOWING DYNAMIC ASSIGNMETNS]
right now the renderer for terminal and mujoco just look at the current state of assignemtns, run teh whole sim, and iterate through teh snaphsots

this separation is already realoly clean
the snapshot size is guarnteed, since there is 1 snapshot for every tick fo time up to MAX_DELTA_TIME.
that means we can instead iterate through the snapshot indicies
we can run the entire simulation on every tick for now
insteasd fo reading from the assignments which is hardcoded at the start of main we cfan read from an AssignmentService
we can make a new fodler services/ and have BaseAssignmentService then InMemoryAssignmentService which impelmetnes the interfaces, since later we want ot do from ddtaabase nto n memorys tore.
but right nwo in mempry osieasier to teswt

what does this servicd have to support?

- getassignemtnsfortime (time) -> return the max assignmetns where assigned at <= time
- setassignments (assignemtns) -> side effect of updating the storage with the new entire lsit of assignments?
- addassignments (assignemtns) -> appends the assignments to whatever data store, in our case the in memory one will jsut be json or something

what are the next steps there

create baseassignmetnservice in services/
define the itnerfaces for it
define what the sideffects are and inputs
