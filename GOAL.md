# Project Goal

We are building an **LLM-in-the-loop multi-robot coordination evaluator**: the simulation runs on an MCP server; an LLM produces task-assignment decisions (e.g. which robot does which task, or how to coordinate object moves); the simulation runs with those decisions and returns metrics (battery, throughput, makespan, etc.) so the LLM can judge and improve the coordination strategy.

A core requirement is **coordinating movement of an object**—i.e. robots physically moving/relaying an object (pick, carry, hand off, deliver)—not only “robot goes to task location and makes progress in place.”
