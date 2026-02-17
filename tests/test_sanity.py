import unittest

from sim.specs import build_default_spec
from sim.state import default_state, DayPlan
from sim.policy import SafetyFirstPolicy
from sim.engine import simulate_day
from sim.runner import enumerate_plans


class TestSanity(unittest.TestCase):
    def test_basic_ranges(self) -> None:
        spec = build_default_spec()
        state = default_state(spec, day_index=2)
        plan = DayPlan(
            supervisor_assignment={
                "security": "LIMEN",
                "conveyor": "STILETTO",
                "burnin_theatre": "CATHEXIS",
                "cognition_brewery": "THRUM",
                "weaving_gallery": "THRUM",
                "brain_forge": "RIVET_WITCH",
            },
            workers_allocated={
                "security": 3,
                "conveyor": 5,
                "burnin_theatre": 2,
                "cognition_brewery": 2,
                "weaving_gallery": 2,
                "brain_forge": 4,
            },
            production_plan="BRAINS",
        )
        policy = SafetyFirstPolicy("safety_first")
        result = simulate_day(spec, state, plan, policy, seed=42)
        for room in result.end_state.rooms.values():
            self.assertGreaterEqual(room.tension, 0.0)
            self.assertLessEqual(room.tension, 100.0)
        self.assertGreaterEqual(result.end_state.workers_count, 0)
        self.assertGreaterEqual(result.ledger.brains_produced, 0.0)
        self.assertGreaterEqual(result.ledger.money_delta, 0.0)
        self.assertGreaterEqual(result.ledger.workers_lost, 0)

    def test_enumerate_plans_respects_capacity(self) -> None:
        plans = list(
            enumerate_plans(
                day_index=1,
                available_rooms=["security", "conveyor"],
                available_supervisors=["LIMEN", "STILETTO"],
                workers_count=3,
                capacity_constraints={"security": 2, "conveyor": 2},
            )
        )
        self.assertTrue(plans)
        for plan in plans:
            total = sum(plan.workers_allocated.values())
            self.assertEqual(total, 3)
            self.assertLessEqual(plan.workers_allocated["security"], 2)
            self.assertLessEqual(plan.workers_allocated["conveyor"], 2)


if __name__ == "__main__":
    unittest.main()
