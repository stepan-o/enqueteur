import unittest

from sim.specs import build_default_spec
from sim.state import default_state, DayPlan
from sim.policy import GreedPolicy
from sim.engine import simulate_day


class TestDeterminism(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = build_default_spec()
        self.initial_state = default_state(self.spec, day_index=3)
        self.plan = DayPlan(
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
        self.policy = GreedPolicy("greed")

    def test_same_seed_is_identical(self) -> None:
        result_a = simulate_day(self.spec, self.initial_state, self.plan, self.policy, seed=123)
        result_b = simulate_day(self.spec, self.initial_state, self.plan, self.policy, seed=123)
        self.assertEqual(result_a.event_log, result_b.event_log)
        self.assertAlmostEqual(result_a.ledger.money_delta, result_b.ledger.money_delta, places=6)
        self.assertAlmostEqual(result_a.ledger.brains_produced, result_b.ledger.brains_produced, places=6)
        self.assertEqual(result_a.ledger.new_workers, result_b.ledger.new_workers)
        self.assertEqual(result_a.ledger.workers_lost, result_b.ledger.workers_lost)

    def test_different_seed_changes_outcome(self) -> None:
        result_a = simulate_day(self.spec, self.initial_state, self.plan, self.policy, seed=123)
        result_b = simulate_day(self.spec, self.initial_state, self.plan, self.policy, seed=124)
        self.assertTrue(
            result_a.event_log != result_b.event_log
            or result_a.ledger.brains_produced != result_b.ledger.brains_produced
        )


if __name__ == "__main__":
    unittest.main()
