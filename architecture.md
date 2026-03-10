# Architecture

This project follows a strict layered architecture.

Dependency direction (one-way only):

primitives → domain → world → algorithms → engine

Lower layers must never import from higher layers.

---

## Layer Responsibilities

### primitives
- Pure value objects
- Immutable where possible
- No internal dependencies

### domain
- Core entities of the simulation
- Depends only on primitives

### world
- Global simulation state
- Aggregates domain objects

### algorithms
- Planning and decision logic
- No simulation loop control
- No engine imports

### engine
- Orchestrates simulation
- Executes steps
- Produces snapshots
- Nothing imports from engine

---

## Hard Rules

- No circular imports
- No cross-layer violations
- Domain must not know algorithms exist
- Engine contains no business logic

---

## Where Should This Go?

1. Pure data? → primitives  
2. Domain behavior? → domain  
3. Global state container? → world  
4. Strategy or planning? → algorithms  
5. Orchestration or execution? → engine