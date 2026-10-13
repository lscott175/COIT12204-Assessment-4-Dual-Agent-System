import json
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from pathlib import Path
from models import MessageSchema
from agents import PlannerAgent, ValidatorAgent

LOG_DIR = Path(__file__).resolve().parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger('Orchestrator')

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / 'agent_system.log', encoding='utf-8')
        ]
    )


class Orchestrator:
    def __init__(self, max_iterations=5, timeout_seconds=10.0):
        if max_iterations < 1 or timeout_seconds <= 0:
            raise ValueError('max_iterations and timeout_seconds must be positive')

        self.max_iterations = max_iterations
        self.timeout_seconds = timeout_seconds
        self.agents = {
            'planner_agent': PlannerAgent(),
            'validator_agent': ValidatorAgent()
        }
        self.message_log = []

    def route_message(self, message: MessageSchema) -> MessageSchema:
        if message.receiver == 'orchestrator':
            return message

        if message.receiver not in self.agents:
            raise ValueError(f"Target agent '{message.receiver}' does not exist")

        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self.agents[message.receiver].process_message,
            message
        )

        try:
            response = future.result(timeout=self.timeout_seconds)

            if not isinstance(response, MessageSchema):
                raise ValueError('Agent returned an invalid message type')

            return response

        except FutureTimeout as exc:
            future.cancel()
            raise TimeoutError(
                f"Agent '{message.receiver}' exceeded {self.timeout_seconds}s timeout"
            ) from exc

        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _record(self, message):
        self.message_log.append(message)
        logger.info(
            'Route: %s -> %s [%s]',
            message.sender,
            message.receiver,
            message.intent
        )

    def _result(self, status, iterations, **kwargs):
        result = {
            'status': status,
            'iterations': iterations,
            **kwargs,
            'logs': [m.model_dump() for m in self.message_log]
        }

        (LOG_DIR / 'last_workflow.json').write_text(
            json.dumps(result, indent=2),
            encoding='utf-8'
        )

        return result

    def run_workflow(self, initial_content, constraints=None):
        self.message_log = []

        try:
            if not isinstance(initial_content, dict) or not str(
                initial_content.get('destination', '')
            ).strip():
                raise ValueError('A destination is required')

            if float(initial_content.get('budget_limit_aud', 0)) <= 0:
                raise ValueError('budget_limit_aud must be positive')

            constraints = constraints if constraints is not None else {
                'max_budget': 1200.0,
                'strict_mode': True
            }

            if float(constraints.get(
                'max_budget', initial_content['budget_limit_aud']
            )) <= 0:
                raise ValueError('max_budget must be positive')

            current = MessageSchema(
                sender='orchestrator',
                receiver='planner_agent',
                intent='propose_plan',
                content=initial_content,
                constraints=constraints
            )

        except (ValueError, TypeError) as exc:
            logger.error('Invalid request: %s', exc)
            return self._result('failed', 0, error=str(exc))

        for step in range(1, self.max_iterations + 1):
            self._record(current)

            if current.receiver == 'orchestrator':
                if current.intent != 'approve_plan':
                    return self._result(
                        'failed', step,
                        error='Unexpected terminal intent'
                    )

                return self._result(
                    'success', step,
                    final_output=current.content
                )

            try:
                current = self.route_message(current)

            except (ValueError, TimeoutError, Exception) as exc:
                logger.exception('Workflow failed during agent execution')
                return self._result('failed', step, error=str(exc))

        # Capture the final outgoing response even when the
        # iteration guardrail stops the workflow.
        self._record(current)

        if current.receiver == 'orchestrator' and current.intent == 'approve_plan':
            return self._result(
                'success',
                self.max_iterations,
                final_output=current.content
            )

        logger.warning('Maximum iterations reached')
        return self._result(
            'max_iterations_exceeded',
            self.max_iterations,
            error='Exceeded maximum allowed interaction steps'
        )


if __name__ == '__main__':
    system = Orchestrator(max_iterations=4)

    result = system.run_workflow(
        {
            'destination': 'Brisbane, QLD',
            'budget_limit_aud': 1200.0,
            'trip_duration_days': 3
        },
        {
            'max_budget': 1200.0,
            'required_format': 'json'
        }
    )

    print(json.dumps(
        {k: v for k, v in result.items() if k != 'logs'},
        indent=2
    ))