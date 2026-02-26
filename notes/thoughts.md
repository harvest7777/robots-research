what do i need before i continue?

id ont want to waste any time
at first, i thoght the llm's role was generating th eassignments
i thought our simulationw as only a means of evaluation for the llm assignments

stuff i arleady have
a simulation swuite that can take in a coordination algorithm to assign robots to tasks, then robots perform those tasks

my professors wants a text2motion essentially
i think he only cares about the most simple usecase
"move this object"
-> translation layer [i do not know what this entails, does it mean to literall go from text to a parseable assignment (robot a, task b), (robot c, task b)] that my simulation can consume and mesaure?]
simulate the choices

he also gave me the document "contextflow.pdf" which has his most updated vision
he definitely just gptd this so some assupmtions about the current implementation and architecture might be wrong
we will also need to descope thish

initial assumptions
llm role: generate assignments
simulation role: evluate assignments

actual
llm role:
simulation role:

this seems like the firrst step... looks like i need to re architect a lot of things here
Run LLM, Planner, and Simulator as separate processes communicating over HTTP or a message queue. Focus entirely on getting the message interfaces right — update_priority, trigger_replan, evaluate_assignment should be structured events, not function calls. Validate correctness on a few fixed scenarios before moving on.
these are all my jubmld thougths

my next tasks shoudl be in this order

- understand the role of the simulation, the llm, and the mcp server
- be able to clearly state one happy path end to end
- descope everythign as much as possible
