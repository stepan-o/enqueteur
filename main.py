"""Loopforge simulation engine demo entrypoint."""

from sim.specs import build_default_spec
from sim.state import default_state, DayPlan
from sim.policy import default_policies
from sim.engine import simulate_day
from sim.runner import SimulationRunner, enumerate_plans
from sim.io import print_day_summary, print_metrics, write_metrics_csv, write_metrics_json


def build_sample_plan() -> DayPlan:
    return DayPlan(
        supervisor_assignment={
            "security": "LIMEN",
            "conveyor": "STILETTO",
            "burnin_theatre": "CATHEXIS",
            "cognition_brewery": "THRUM",
            "weaving_gallery": "THRUM",
            "brain_forge": "RIVET_WITCH",
        },
        workers_allocated={
            "security": 4,
            "conveyor": 6,
            "burnin_theatre": 3,
            "cognition_brewery": 2,
            "weaving_gallery": 2,
            "brain_forge": 5,
        },
        production_plan="BRAINS",
    )


def main() -> None:
    spec = build_default_spec()
    state = default_state(spec, day_index=3)
    plan = build_sample_plan()
    policies = default_policies()

    print("Running example day simulation...")
    day_result = simulate_day(spec, state, plan, policies[1], seed=101)
    print_day_summary(day_result)

    runner = SimulationRunner(spec, state)
    metrics = runner.run_monte_carlo(n=50, day_index=3, plan=plan, policy=policies[1], seed0=1000)
    print_metrics(metrics, label="Monte Carlo Summary")
    write_metrics_csv("runs/summary.csv", metrics)
    write_metrics_json("runs/summary.json", metrics)

    rooms = ["security", "conveyor", "burnin_theatre"]
    supervisors = ["LIMEN", "STILETTO", "CATHEXIS"]
    capacity = {room_id: spec.rooms[room_id].capacity for room_id in rooms}
    plans = list(enumerate_plans(3, rooms, supervisors, workers_count=6, capacity_constraints=capacity))
    ranked = runner.evaluate_strategies(plans[:6], policies[:3], n_mc=10, seed0=2000, day_index=3)

    print("Top strategies (money_delta mean):")
    for item in ranked[:3]:
        print(
            f"  policy={item.policy_name} money_mean={item.metrics.metrics['money_delta'].mean:.2f} "
            f"plan_workers={item.plan.workers_allocated}"
        )


if __name__ == "__main__":
    main()
