from simulation_models.assignment import RobotId
from simulation_models.capability import Capability
from simulation_models.environment import Environment
from simulation_models.position import Position
from simulation_models.robot import Robot
from simulation_models.robot_state import RobotState
from simulation_models.simulation import Simulation
from simulation_models.task import Task, TaskId, TaskType
from simulation_models.task_state import TaskState, TaskStatus
from simulation_models.time import Time


def _create_sim_fixture() -> Simulation:
    robot_id = RobotId(1)
    task_id = TaskId(1)

    robot = Robot(id=robot_id, capabilities=frozenset(), speed=1.0)
    task = Task(
        id=task_id,
        type=TaskType.ROUTINE_INSPECTION,
        priority=1,
        required_work_time=Time(1),
    )
    robot_state = RobotState(robot_id=robot_id, position=Position(0.0, 0.0))
    task_state = TaskState(task_id=task_id)

    return Simulation(
        environment=Environment(width=5, height=5),
        robots=[robot],
        tasks=[task],
        robot_states={robot_id: robot_state},
        task_states={task_id: task_state},
    )


def test_task_can_be_worked_on_if_at_least_one_robot_meets_required_capabilities():
    pass

def test_task_is_only_worked_on_by_robots_with_required_capabilities():
    pass

def test_failed_task_can_not_be_worked_on():
    pass

def test_completed_task_can_not_be_worked_on():
    pass

def task_can_not_be_worked_on_if_robots_are_not_within_spatial_constraint():
    pass

def test_task_can_not_be_worked_on_if_no_robot_has_the_required_capabilities():
    pass
