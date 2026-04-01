from dataclasses import dataclass, field


@dataclass(frozen=True)
class AgentCallRecord:
    """Records the cost and performance of a single agent decision (one planning step).

    One record covers the full tool loop for a single assignment decision — potentially
    multiple LLM hits — so tokens and latency are accumulated across all rounds.
    """

    timestamp: float        # time.time() at the start of the decision
    latency_ms: int         # wall time for the entire tool loop
    tokens_in: int          # total prompt tokens across all LLM hits in this decision
    tokens_out: int         # total completion tokens across all LLM hits in this decision
    tool_rounds: int        # number of tool call iterations before final response
    tool_call_counts: dict[str, int] = field(default_factory=dict)
    # tool_call_counts: how many times each tool was called during this decision,
    # e.g. {"get_state": 2, "write_assignments": 1}. Reveals over-inspection or
    # repeated writes.
    truncated_by_tool_limit: bool = False
    # truncated_by_tool_limit: True if max_tool_calls cut the agent off before it
    # produced a final response. Indicates the tool limit may be too tight.
