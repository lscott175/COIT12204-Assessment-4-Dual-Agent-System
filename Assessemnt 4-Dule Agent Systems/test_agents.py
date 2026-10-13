import time
import unittest
from orchestrator import Orchestrator
from models import MessageSchema

REQUEST = {
    'destination': 'Brisbane, QLD',
    'budget_limit_aud': 1200.0,
    'trip_duration_days': 3
}


class TestWorkflow(unittest.TestCase):

    def test_successful_workflow(self):
        result = Orchestrator().run_workflow(REQUEST)

        self.assertEqual(result['status'], 'success')
        self.assertEqual(
            [m['intent'] for m in result['logs']],
            ['propose_plan', 'validate_itinerary', 'approve_plan']
        )

    def test_revision_preserves_destination(self):
        result = Orchestrator().run_workflow(
            REQUEST,
            {'max_budget': 450.0}
        )

        self.assertEqual(result['status'], 'success')
        self.assertEqual(
            result['final_output']['final_itinerary']['destination'],
            'Brisbane, QLD'
        )
        self.assertEqual(
            result['final_output']['final_itinerary']['total_estimated_cost'],
            400.0
        )
        self.assertIn(
            'request_revision',
            [m['intent'] for m in result['logs']]
        )

    def test_unaffordable_budget_stops(self):
        result = Orchestrator(max_iterations=5).run_workflow(
            REQUEST,
            {'max_budget': 100.0}
        )

        self.assertEqual(result['status'], 'max_iterations_exceeded')

    def test_invalid_receiver(self):
        msg = MessageSchema(
            sender='test',
            receiver='unknown',
            intent='propose_plan',
            content={}
        )

        with self.assertRaises(ValueError):
            Orchestrator().route_message(msg)

    def test_invalid_input(self):
        result = Orchestrator().run_workflow({
            'destination': '',
            'budget_limit_aud': -1
        })

        self.assertEqual(result['status'], 'failed')

    def test_timeout(self):
        class SlowAgent:
            def process_message(self, message):
                time.sleep(0.2)
                return message

        system = Orchestrator(timeout_seconds=0.01)
        system.agents['planner_agent'] = SlowAgent()

        result = system.run_workflow(REQUEST)

        self.assertEqual(result['status'], 'failed')
        self.assertIn('timeout', result['error'])


if __name__ == '__main__':
    unittest.main()