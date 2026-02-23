the mcp is the interface which the llm will interact with to read state and write events

the db (state store) is the persistence layer which the simulation will read state from

the message queue is an implementation detail and is how we will handel event writes from the simulation. in the background, the mcp will talk to this queue in teh background

the simulation is still responsible for taking in an arbritriary state, executing the assigned tasks from the llm read from the cache, then updating state (this time through a push to a db, no longer stored as a field of the simulation class)

the deployment of the cache and mcp is where the backend runs on, keep it cloud or edge for now to be simple
