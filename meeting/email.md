For the project,
I make a workflow as below:
image.png
Is that the structure from your description? If so, I have following

    layered planning architectures are well-established in robotics (e.g., Task and Motion Planning).
    LLM-as-strategic-layer has precedent in SayCan, LLM-Planner, and similar works (https://arxiv.org/pdf/2209.09874 https://link.springer.com/article/10.1007/s10514-023-10131-7). At this step we can not differentiate from them...

Our main novelty or spotlight is the next step (AI helps me to make bulleted steps):

    Once the modules (simulated robots) are split across containers or serverless functions, they can only talk over the network. That means update_priority, trigger_replan, and evaluate_assignment are no longer function calls — they become structured messages over a queue (e.g. Kafka, Redis Streams) or explicit REST/gRPC calls. The design decision of which communication pattern to use for which action is itself a research question, not just an implementation detail.

    New mechanism needed: async decoupling. In the current single-process design, trigger_replan is synchronous — the LLM calls it and waits for the new plan. In a distributed setting the Planner lives on a different machine, so you have to make an explicit choice: does the LLM block and wait for the replan result, or does it fire-and-forget and let the Planner publish the new plan whenever it's ready? Each option has real tradeoffs — blocking preserves consistency but adds latency; fire-and-forget reduces latency but means the LLM may keep issuing priority updates based on an outdated plan. Designing, implementing, and measuring this tradeoff is one of the most concrete and defensible research contributions in the whole project.

Then AI gives me a plan (but I think a bit far away from this moment, but help to frame the picture):

Phase 1 — Single-Machine Prototype

Run LLM, Planner, and Simulator as separate processes communicating over HTTP or a message queue. Focus entirely on getting the message interfaces right — update_priority, trigger_replan, evaluate_assignment should be structured events, not function calls. Validate correctness on a few fixed scenarios before moving on.

Phase 2 — Dockerize and Study Distributed Problems

Package each module into its own container and wire them with docker-compose. Two concrete problems will surface: (1) re-plan latency — after trigger_replan is fired, what do robots do while the Planner is recomputing? (2) state staleness — the LLM and Planner may act on different snapshots of robot states. Measure how often this happens and what it costs.

Phase 3 — Serverless and Deployment Mismatch

Push the Planner and evaluate_assignment jobs to serverless (AWS Lambda or LocalStack locally). The core tension to study: the Planner is compute-heavy and long-running, which conflicts with serverless cold-start and timeout constraints. Quantify this mismatch — when does serverless help, when does it hurt, and which modules actually benefit from it. That tradeoff analysis is your main research finding in this phase.
———————————————————————————————————
Overall, our novelty is the next step: we need to revisit previous project description or make a new plan as we go to this step. So current step (what you are doing) is a bit flexible, you can use any ways you feel practical to accomplish it. Then we need to dip into the novelty of future steps, as we may have meeting with Dr. Tao or other collaborators later. Meanwhile, I will find exporter who is skilled at CV and AI that help us to reformat your current step, we can do it later after your simulation part is done.

Best,
Hailu
