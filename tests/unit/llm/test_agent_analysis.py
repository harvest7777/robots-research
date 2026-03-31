"""
Tests for AgentAnalysis.

Focused on observable behavior — what the analysis reports given a set of
call records — not on how it computes it internally.
"""

import pytest
from llm.agent_call_record import AgentCallRecord
from llm.agent_analysis import AgentAnalysis


def _record(
    tokens_in: int = 100,
    tokens_out: int = 50,
    latency_ms: int = 500,
    tool_rounds: int = 1,
    timestamp: float = 0.0,
) -> AgentCallRecord:
    return AgentCallRecord(
        timestamp=timestamp,
        latency_ms=latency_ms,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        tool_rounds=tool_rounds,
    )


# ---------------------------------------------------------------------------
# Empty records
# ---------------------------------------------------------------------------

def test_no_calls_reports_zero_totals():
    analysis = AgentAnalysis.from_records([])
    assert analysis.total_calls == 0
    assert analysis.total_tokens_in == 0
    assert analysis.total_tokens_out == 0


def test_no_calls_reports_no_latency_stats():
    analysis = AgentAnalysis.from_records([])
    assert analysis.mean_latency_ms is None
    assert analysis.min_latency_ms is None
    assert analysis.max_latency_ms is None


def test_no_calls_reports_no_tool_round_stats():
    analysis = AgentAnalysis.from_records([])
    assert analysis.mean_tool_rounds is None


# ---------------------------------------------------------------------------
# Single call
# ---------------------------------------------------------------------------

def test_single_call_totals_match_record():
    record = _record(tokens_in=200, tokens_out=80)
    analysis = AgentAnalysis.from_records([record])
    assert analysis.total_calls == 1
    assert analysis.total_tokens_in == 200
    assert analysis.total_tokens_out == 80


def test_single_call_latency_stats_all_equal_that_call():
    record = _record(latency_ms=750)
    analysis = AgentAnalysis.from_records([record])
    assert analysis.mean_latency_ms == 750
    assert analysis.min_latency_ms == 750
    assert analysis.max_latency_ms == 750


def test_single_call_tool_rounds_mean_equals_that_call():
    record = _record(tool_rounds=3)
    analysis = AgentAnalysis.from_records([record])
    assert analysis.mean_tool_rounds == 3


# ---------------------------------------------------------------------------
# Multiple calls — token aggregation
# ---------------------------------------------------------------------------

def test_tokens_are_summed_across_all_calls():
    records = [
        _record(tokens_in=100, tokens_out=40),
        _record(tokens_in=200, tokens_out=60),
        _record(tokens_in=300, tokens_out=20),
    ]
    analysis = AgentAnalysis.from_records(records)
    assert analysis.total_tokens_in == 600
    assert analysis.total_tokens_out == 120


def test_call_count_matches_number_of_records():
    records = [_record() for _ in range(7)]
    analysis = AgentAnalysis.from_records(records)
    assert analysis.total_calls == 7


# ---------------------------------------------------------------------------
# Multiple calls — latency stats
# ---------------------------------------------------------------------------

def test_min_latency_is_the_fastest_call():
    records = [_record(latency_ms=ms) for ms in [300, 100, 500, 200]]
    analysis = AgentAnalysis.from_records(records)
    assert analysis.min_latency_ms == 100


def test_max_latency_is_the_slowest_call():
    records = [_record(latency_ms=ms) for ms in [300, 100, 500, 200]]
    analysis = AgentAnalysis.from_records(records)
    assert analysis.max_latency_ms == 500


def test_mean_latency_is_average_across_calls():
    records = [_record(latency_ms=ms) for ms in [200, 400, 600]]
    analysis = AgentAnalysis.from_records(records)
    assert analysis.mean_latency_ms == pytest.approx(400.0)


# ---------------------------------------------------------------------------
# Multiple calls — tool rounds
# ---------------------------------------------------------------------------

def test_mean_tool_rounds_is_average_across_calls():
    records = [_record(tool_rounds=r) for r in [1, 2, 3]]
    analysis = AgentAnalysis.from_records(records)
    assert analysis.mean_tool_rounds == pytest.approx(2.0)


def test_mean_tool_rounds_handles_fractional_average():
    records = [_record(tool_rounds=r) for r in [1, 2]]
    analysis = AgentAnalysis.from_records(records)
    assert analysis.mean_tool_rounds == pytest.approx(1.5)
