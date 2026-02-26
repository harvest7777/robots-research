the mcp is the interface which the llm will interact with to read state and write events

the db (state store) is the persistence layer which the simulation will read state from

the message queue is an implementation detail and is how we will handel event writes from the simulation. in the background, the mcp will talk to this queue in teh background

the simulation is still responsible for taking in an arbritriary state, executing the assigned tasks from the llm read from the cache, then updating state (this time through a push to a db, no longer stored as a field of the simulation class)

the deployment of the cache and mcp is where the backend runs on, keep it cloud or edge for now to be simple

professor response
the mcp is the interface which the llm will interact with to read state and write events [looks good]

the db (state store) is the persistence layer which the simulation will read state from [so the “state” means action plan from llm?]

the message queue is an implementation detail and is how we will handel event writes from the simulation. in the background, the mcp will talk to this queue in teh background [okay, any design that can support it looks fine]

the simulation is still responsible for taking in an arbritriary state, executing the assigned tasks from the llm read from the cache, then updating state (this time through a push to a db, no longer stored as a field of the simulation class) [means at runtime, updated state(tasks) will be instantly write to the db for stored state? Looks fine]

the deployment of the cache and mcp is where the backend runs on, keep it cloud or edge for now to be simple [you need to try to see if cloud/edge is a good option, also think about the case in future when we do scalable evaluation, is that still practical at runtime?]
So the implementation details are not that important actually, as you can support the design or story, we don’t need to make each technical decision perfectly at this time. After produce a demo, we can look back to see where to optimize.

my response back
Gotcha, thank you professor!

To answer your questions
"state" is the states of all robots and tasks
yes at runtime state is written to db
will look into scalability for deployment
