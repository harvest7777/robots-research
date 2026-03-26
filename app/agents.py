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


def KAT_CODER_PRO_AGENT(store: BaseSimulationStore, assignment_service: BaseAssignmentService) -> AssignmentAgent:
    return AssignmentAgent(
        model="openai/ep-8d4p2p-1774502943933981149",
        api_base="https://vanchin.streamlake.ai/api/gateway/v1/endpoints",
        api_key=os.getenv("STREAMLAKE_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_SYSTEM,
    )


def KAT_CODER_EXP_AGENT(store: BaseSimulationStore, assignment_service: BaseAssignmentService) -> AssignmentAgent:
    return AssignmentAgent(
        model="openai/ep-a23s52-1774502943903035372",
        api_base="https://vanchin.streamlake.ai/api/gateway/v1/endpoints",
        api_key=os.getenv("STREAMLAKE_API_KEY"),
        store=store,
        assignment_service=assignment_service,
        system=_SYSTEM,
    )


def KAT_CODER_AIR_AGENT(store: BaseSimulationStore, assignment_service: BaseAssignmentService) -> AssignmentAgent:
    return AssignmentAgent(
        model="openai/ep-itub30-1774502943921641769",
        api_base="https://vanchin.streamlake.ai/api/gateway/v1/endpoints",
        api_key=os.getenv("STREAMLAKE_API_KEY"),
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
