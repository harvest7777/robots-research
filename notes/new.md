raw thoughts
we want the llm to be able to change the trajectory of something in real time
lets have this be as simple as possible
right now how does rendering work

right now when wthe llm lmakes ad ecision we dont even insert into the table with our decision
we need to refactor to have a few layers here

we want thsi functionality
we can run the simlaution

we just need a way for the assignments to work with the database, can figure out later
the goal is for the assignments to be overrideable
we can support a mostrecentassignment for each robot?
to override an assignment at any point in time, we just need to insert a new assignment
now what about the rendedring part, this is the "wow" factor my professor cares about
-> my udnerlying arcthiecture is this
we can just have a keyvalue store at runtime here it doesnt have to be crazy

rendering is going to be tricky
how do we render this? our rendering engine takes a snapshot object and converts it to a render frame
then it displays it
is it possible for this process to be dynamic?
YES. we dotn need th eentire frame sequence predetermined

what are we blocked by here
the timing part will be kind of tricky
right nwo the way our simulation works is by having a fuck ton of frames
rendering whatever frame is next
adn we sped up/slow down actual rendeirng time with time.sleep
what if instead, we did not care t the time.sleep or anythign and we instead just rendered when we had a new snapshot?
no. that would mean the snapshot has to be the thing getting inserted in a queue liek fashion
hwo about we decouple the simulation from the task assignmetns completely

task, time assigned
we run the simulation determiniistically
rendering is done through iterating through to the next time
we can keep our time.sleep()
perfect.
we just cant let the ai overwrite hsitory of the simulation, or else w e will get snapping behavior
so we need this contract

a simulation simulates task sisgnmetns
assignment has as new field, "assign_at"

how do we determine assign at thoguh?
how woudl this work with siple sasign
with the llm?

with the llm if asap, jsut assign at the ext tick
for simple assign just assign at the dcurrent tick as the tasks complete

the simulation runs its entire way through assignments, that conract does not change
what chanes is who we ar epicking what asignment to run so we can stream them in this is the logicla next step

clear everythign up

- we need to refactor the Assignment type to also have a assign_at field of type Time
- we need to refactor our Simulation to re-assign tasks based on the simluation's current time, robot and task last assigned_at time, at the assignment's assign_at time. I have left comments for this
- these things will be broken in their current state:
  simple assign doesnt have any knowledge of time

\/ i think this can be worried about later, having one assignment for main is actually fien right now, we can go off this singular assignment and have the llm build off of it which will hlep us test the "reassignment" part

- in main, we call simple assign only onc so the assignments never really actually changeo

right now i am NOT concerned with the database, NOT concerned with the MCP, NOT concerned with the llm
i jus twant to get the contracts straight and test the new implementation, ensuring nothingelse broke
