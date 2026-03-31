from dataclasses import dataclass


@dataclass(frozen=True)
class AgentCallRecord:
    """Records the cost and performance of a single agent decision (one planning step).

    One record covers the full tool loop for a single assignment decision — potentially
    multiple LLM hits — so tokens and latency are accumulated across all rounds.
    """

    timestamp: float  # time.time() at the start of the decision
    latency_ms: int  # wall time for the entire tool loop
    tokens_in: int  # total prompt tokens across all LLM hits in this decision
    tokens_out: int  # total completion tokens across all LLM hits in this decision
    tool_rounds: int  # number of tool call iterations before final response
