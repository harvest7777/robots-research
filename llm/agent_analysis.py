"""
AgentAnalysis

Pure value object aggregated from a list of AgentCallRecords produced
during a simulation run. Contains no coupling to the runner, simulation
state, or LLM provider — only the records matter.

Metrics
-------
total_calls       : number of planning decisions made
total_tokens_in   : sum of prompt tokens across all calls
total_tokens_out  : sum of completion tokens across all calls
mean_latency_ms   : average wall time per decision; None if no calls
min_latency_ms    : fastest decision; None if no calls
max_latency_ms    : slowest decision; None if no calls
mean_tool_rounds  : average tool loop iterations per decision; None if no calls
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from llm.agent_call_record import AgentCallRecord


@dataclass(frozen=True)
class AgentAnalysis:
    total_calls: int
    total_tokens_in: int
    total_tokens_out: int
    mean_latency_ms: float | None
    min_latency_ms: int | None
    max_latency_ms: int | None
    mean_tool_rounds: float | None

    def to_json_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_records(cls, records: list[AgentCallRecord]) -> AgentAnalysis:
        if not records:
            return cls(
                total_calls=0,
                total_tokens_in=0,
                total_tokens_out=0,
                mean_latency_ms=None,
                min_latency_ms=None,
                max_latency_ms=None,
                mean_tool_rounds=None,
            )

        n = len(records)
        return cls(
            total_calls=n,
            total_tokens_in=sum(r.tokens_in for r in records),
            total_tokens_out=sum(r.tokens_out for r in records),
            mean_latency_ms=sum(r.latency_ms for r in records) / n,
            min_latency_ms=min(r.latency_ms for r in records),
            max_latency_ms=max(r.latency_ms for r in records),
            mean_tool_rounds=sum(r.tool_rounds for r in records) / n,
        )
