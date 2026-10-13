import logging
from models import MessageSchema

logger = logging.getLogger('AgentSystem')

class BaseAgent:
    def __init__(self, name, role):
        self.name, self.role = name, role

    def process_message(self, message):
        raise NotImplementedError


class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__('planner_agent', 'Task Decomposer & Itinerary Drafter')

    def process_message(self, message: MessageSchema) -> MessageSchema:
        logger.info('%s RECEIVED %s from %s', self.name, message.intent, message.sender)
        payload = message.content
        destination = payload['destination']
        budget = float(payload['budget_limit_aud'])
        revised = message.intent == 'request_revision'

        if revised:
            logger.info('Planner revising: %s', payload.get('feedback', ''))

        steps = ([
            {'step_id': 1, 'activity': 'Budget Accommodation', 'estimated_cost_aud': 350.0, 'details': 'Revised budget hotel'},
            {'step_id': 2, 'activity': 'Riverfire Event Access', 'estimated_cost_aud': 50.0, 'details': 'Standard viewing pass'},
        ] if revised else [
            {'step_id': 1, 'activity': 'Hotel Accommodation', 'estimated_cost_aud': 450.0, 'details': '3 nights central hotel'},
            {'step_id': 2, 'activity': 'Riverfire Event Access & Transport', 'estimated_cost_aud': 50.0, 'details': 'Public transit and viewing pass'},
        ])

        response = MessageSchema(
            sender=self.name,
            receiver='validator_agent',
            intent='validate_itinerary',
            content={
                'destination': destination,
                'budget_limit_aud': budget,
                'trip_duration_days': payload.get('trip_duration_days', 3),
                'itinerary_steps': steps,
                'total_estimated_cost': sum(s['estimated_cost_aud'] for s in steps),
                'revision_notes': 'Revised based on feedback' if revised else 'Initial draft'
            },
            constraints=message.constraints
        )

        logger.info('%s SENT %s to %s', self.name, response.intent, response.receiver)
        return response


class ValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__('validator_agent', 'Constraint Checker & Reviewer')

    def process_message(self, message: MessageSchema) -> MessageSchema:
        logger.info('%s RECEIVED %s from %s', self.name, message.intent, message.sender)
        p = message.content
        steps = p.get('itinerary_steps')

        if not isinstance(steps, list) or not steps:
            raise ValueError('Itinerary must contain at least one step')

        costs = [float(s['estimated_cost_aud']) for s in steps]

        if any(c < 0 for c in costs) or abs(
            sum(costs) - float(p['total_estimated_cost'])
        ) > 0.01:
            raise ValueError('Invalid or inconsistent itinerary costs')

        limit = min(
            float(p['budget_limit_aud']),
            float((message.constraints or {}).get('max_budget', p['budget_limit_aud']))
        )

        if sum(costs) > limit:
            response = MessageSchema(
                sender=self.name,
                receiver='planner_agent',
                intent='request_revision',
                content={
                    'feedback': f'Total cost ${sum(costs):.2f} exceeds budget ${limit:.2f}',
                    'failed_steps': steps,
                    'destination': p['destination'],
                    'budget_limit_aud': p['budget_limit_aud'],
                    'trip_duration_days': p.get('trip_duration_days', 3)
                },
                constraints=message.constraints
            )
        else:
            response = MessageSchema(
                sender=self.name,
                receiver='orchestrator',
                intent='approve_plan',
                content={
                    'status': 'approved',
                    'final_itinerary': p,
                    'validation_message': 'All constraints met successfully.'
                },
                constraints=message.constraints
            )

        logger.info('%s SENT %s to %s', self.name, response.intent, response.receiver)
        return response