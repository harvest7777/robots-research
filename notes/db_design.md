i dont need copmlex joisn
i want the source of truth of models to stem from the simulation, not the database
im leaning towardes these tables

simulations
id
robot_states
id, jsonb
task_statse
id, jsonb
snapshots
id, step, jsonb

orm vs no orm?
there is not much business requirements we have to enforce
we aren tdoing crud heavy logic
