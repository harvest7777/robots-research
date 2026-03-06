so weve made assignments dynamic through the assignemnt service, we cN See hwo it is used in main.py to arbritarly overwrite assignemtns tarting ast some simple time which changes robot behavior

the next step si plugign gthis into our mcp

this means well hneed a way for the mcp server and main program to be synced
with the in memory store, this is tricky becUSE whenw e start a new terminal and use oru mcp, the mrmoy is reset, this is not shared memory

we could fix this through threadin but id say th tis overly compolaiteedd
writing to a inmemory database might be easier.

we also need to sync other things for in memory testing like the current scenario were simulating for and the time were on right?
shoudl we make services for that? then we can plug nad play these things when we move back to our database

mayb ewe can also have a basesimulationstateservice which holds state liek current time of the simulation and current state of all the robots and tasks

this way what is each ting responsibel fofr
the mcp is only responsible for writing to a shared simluation assignments
to write accurate assignment it needs to reasd from basesimulationservice to get he state for the current time,and states of robots and tasks

right now there is a problem
our states are drifintg out of sync
the state is necessary for the llm to make good decisiosn

we need to writ eour state somehow, that is ther sopnbiility of whatever the simualtion is running on
simulatino si responsibel for
writing assignments once at the start
reading assignments from the assignmentservice
runnigni the assignments
writing to the simulation state service

i thik this is what we need at minimum. what do you think?
