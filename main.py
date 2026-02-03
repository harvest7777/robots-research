from simulation_models import (
    Environment,
    Robot,
    Task,
    TaskType,
    Simulation,
    NearestFeasibleCoordinator,
)


def main():
    # Create a 100x100 warehouse environment
    env = Environment(width=100, height=100)

    # Add some obstacles (blocked cells)
    for x in range(40, 60):
        for y in range(45, 55):
            env.set_blocked(x, y)

    # Create a heterogeneous fleet
    robots = [
        Robot(id="inspector_1", x=10, y=10, speed_mps=3.0, capabilities={"inspect"}),
        Robot(id="inspector_2", x=90, y=90, speed_mps=3.0, capabilities={"inspect"}),
        Robot(id="repair_bot", x=50, y=10, speed_mps=1.5, capabilities={"inspect", "repair"}),
        Robot(id="data_collector", x=50, y=90, speed_mps=2.0, capabilities={"inspect", "collect_data"}),
        Robot(id="multi_purpose", x=10, y=50, speed_mps=2.0, capabilities={"inspect", "repair", "collect_data"}),
    ]

    # Create heterogeneous tasks at various locations
    tasks = [
        Task(id="t1", task_type=TaskType.ROUTINE_INSPECTION, x=20, y=20,
             required_capabilities={"inspect"}, duration_est_s=30),
        Task(id="t2", task_type=TaskType.ROUTINE_INSPECTION, x=80, y=80,
             required_capabilities={"inspect"}, duration_est_s=25),
        Task(id="t3", task_type=TaskType.PREVENTIVE_MAINTENANCE, x=30, y=70,
             required_capabilities={"inspect", "repair"}, duration_est_s=90),
        Task(id="t4", task_type=TaskType.ANOMALY_INVESTIGATION, x=70, y=30,
             required_capabilities={"inspect", "collect_data"}, duration_est_s=60),
        Task(id="t5", task_type=TaskType.EMERGENCY_RESPONSE, x=15, y=85,
             required_capabilities={"repair"}, duration_est_s=45),
        Task(id="t6", task_type=TaskType.ROUTINE_INSPECTION, x=85, y=15,
             required_capabilities={"inspect"}, duration_est_s=20),
        Task(id="t7", task_type=TaskType.PREVENTIVE_MAINTENANCE, x=60, y=60,
             required_capabilities={"repair", "collect_data"}, duration_est_s=120),
    ]

    print("=== Distributed Task Allocation Simulation ===\n")
    print(f"Environment: {env.width}x{env.height} grid")
    print(f"Robots: {len(robots)}")
    for r in robots:
        print(f"  - {r.id}: pos=({r.x}, {r.y}), speed={r.speed_mps}m/s, caps={r.capabilities}")
    print(f"\nTasks: {len(tasks)}")
    for t in tasks:
        print(f"  - {t.id}: {t.task_type.value} at ({t.x}, {t.y}), "
              f"requires={t.required_capabilities}, duration={t.duration_est_s}s")

    # Run simulation
    sim = Simulation(
        env=env,
        robots=robots,
        tasks=tasks,
        coordinator=NearestFeasibleCoordinator(),
        dt=1.0,
    )

    print("\n--- Running simulation ---\n")
    results = sim.run(max_steps=500)

    print("=== Results ===")
    print(f"Makespan: {results['makespan_s']:.1f}s")
    print(f"Avg task completion time: {results['avg_task_completion_time_s']:.1f}s")
    print(f"Total travel distance: {results['total_travel_distance_m']:.1f}m")
    print(f"Tasks completed: {results['tasks_completed']}/{len(tasks)}")
    print(f"Tasks failed: {results['tasks_failed']}")

    print("\n--- Final robot positions ---")
    for r in robots:
        print(f"  {r.id}: ({r.x:.1f}, {r.y:.1f}), traveled={r.total_distance_traveled:.1f}m")


if __name__ == "__main__":
    main()
