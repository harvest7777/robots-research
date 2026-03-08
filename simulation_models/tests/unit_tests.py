from simulation_models.simulation import Simulation


def _create_sim_() -> Simulation:
    pass

# content of test_sample.py
def func(x):
    return x + 1


def test_answer():
    assert func(3) == 5


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