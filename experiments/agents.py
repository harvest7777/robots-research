import os
from dotenv import load_dotenv

from llm.agent import AssignmentAgent
from simulation.engine_rewrite.services.base_assignment_service import BaseAssignmentService
from simulation.engine_rewrite.services.base_simulation_store import BaseSimulationStore

load_dotenv()

_SYSTEM = (
    "You are a robot task assignment system. "
    "Call get_state to inspect the current simulation state, "
    "then call write_assignments to assign each robot to the highest-priority "
    "task it is capable of performing. Prioritise tasks by their priority field."
)


def ASI1_AGENT(store: BaseSimulationStore, assignment_service: BaseAssignmentService) -> AssignmentAgent:
    return AssignmentAgent(
        model="openai/asi1",
        api_base="https://api.asi1.ai/v1",
        api_key=os.getenv("ASI_ONE_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_SYSTEM,
    )


def GPT4O_AGENT(store: BaseSimulationStore, assignment_service: BaseAssignmentService) -> AssignmentAgent:
    return AssignmentAgent(
        model="openai/gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_SYSTEM,
    )


def GEMINI_AGENT(store: BaseSimulationStore, assignment_service: BaseAssignmentService) -> AssignmentAgent:
    return AssignmentAgent(
        model="gemini/gemini-2.0-flash",
        api_key=os.getenv("GOOGLE_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_SYSTEM,
    )


def CLAUDE_AGENT(store: BaseSimulationStore, assignment_service: BaseAssignmentService) -> AssignmentAgent:
    return AssignmentAgent(
        model="anthropic/claude-haiku-4-5-20251001",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_SYSTEM,
    )


MODEL_REGISTRY = {
    "gpt-4o":           GPT4O_AGENT,
    "gemini-2.0-flash": GEMINI_AGENT,
    "claude-haiku":     CLAUDE_AGENT,
    "asi1":             ASI1_AGENT,
}
