# Project Goal

We are building an **LLM-in-the-loop multi-robot coordination evaluator**: the simulation will run on an MCP server; an LLM produces task-assignment decisions (e.g. who does which task, or how to coordinate object moves); we run the simulation with those decisions and return metrics (battery, throughput, makespan, etc.) so the LLM can judge and improve its coordination strategy.

A core requirement from the professor is **coordinating movement of an object**—i.e. robots physically moving/relaying an object (pick, carry, hand off, deliver)—not only “robot goes to task location and makes progress in place.”
