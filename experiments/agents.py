import os
from dotenv import load_dotenv

from llm.agent import AssignmentAgent
from simulation.engine_rewrite.services.base_assignment_service import (
    BaseAssignmentService,
)
from simulation.engine_rewrite.services.base_simulation_store import BaseSimulationStore

load_dotenv()

_SYSTEM_BASE = (
    "You are a robot task assignment system. "
    "Call get_state to inspect the current simulation state, "
    "then call write_assignments to assign each robot to the highest-priority "
    "task it is capable of performing. Prioritise tasks by their priority field."
)


def _build_system(rules: str | None) -> str:
    if rules:
        return _SYSTEM_BASE + "\n\n# Override Rules\n" + rules
    return _SYSTEM_BASE


def ASI1_AGENT(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openai/asi1",
        api_base="https://api.asi1.ai/v1",
        api_key=os.getenv("ASI_ONE_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )

def GEMMA_3_27B(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/google/gemma-3-27b-it:free",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


def GPT_OSS_20B(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/openai/gpt-oss-20b:free",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


def GPT4O_AGENT(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/openai/gpt-4o",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


def GEMINI_AGENT(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/google/gemini-2.0-flash-exp:free",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


def CLAUDE_AGENT(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/anthropic/claude-3-haiku",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


def DEEPSEEK_V3_AGENT(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/deepseek/deepseek-chat-v3-5",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


def DEEPSEEK_R1_AGENT(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/deepseek/deepseek-r1",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


def LLAMA_3_3_70B_AGENT(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/meta-llama/llama-3.3-70b-instruct",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


def QWEN3_32B_AGENT(
    store: BaseSimulationStore,
    assignment_service: BaseAssignmentService,
    rules: str | None = None,
) -> AssignmentAgent:
    return AssignmentAgent(
        model="openrouter/qwen/qwen3-32b",
        api_base="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_build_system(rules),
    )


MODEL_REGISTRY = {
    "gpt-4o": GPT4O_AGENT,
    "gemini-2.0-flash": GEMINI_AGENT,
    "claude-haiku": CLAUDE_AGENT,
    "asi1": ASI1_AGENT,
    "gemma-3-27b": GEMMA_3_27B,
    "gpt-oss-20b": GPT_OSS_20B,
    "deepseek-v3": DEEPSEEK_V3_AGENT,
    "deepseek-r1": DEEPSEEK_R1_AGENT,
    "llama-3.3-70b": LLAMA_3_3_70B_AGENT,
    "qwen3-32b": QWEN3_32B_AGENT,
}
