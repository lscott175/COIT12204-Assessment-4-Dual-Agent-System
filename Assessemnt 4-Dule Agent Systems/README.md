# Smart Travel Companion – Two-Agent System

A demonstration of a **Planner Agent** and **Validator Agent** communicating through a structured Pydantic message schema and an orchestrator.

This is a rule-based simulation, not a live AI model or travel-booking service. Prices and activities are illustrative and are not verified live travel data.

## Setup

Requires Python 3.10+.

Install dependencies:

```bash
python -m pip install -r requirements.txt or py -m pip install -r requirements.txt
```

Run the application:

```bash
python orchestrator.py or py orchestrator.py
```

Run automated tests:

```bash
python -m unittest -v test_agents.py or py -m unittest -v test_agents.py
```

## Project Structure

- `models.py` – Validated message schema and response model.
- `agents.py` – Planner Agent and Validator Agent implementations.
- `orchestrator.py` – Message routing, iteration limits, timeouts, error handling, and log persistence.
- `test_agents.py` – Six automated tests covering successful workflows, revisions, budget restrictions, invalid receivers, invalid inputs, and timeouts.
- `requirements.txt` – Required Python dependencies.
- `logs/agent_system.log` – Runtime communication and error logs (generated).
- `logs/last_workflow.json` – Most recent workflow result and message history (generated).

## Agent Coordination

The orchestrator sends a `propose_plan` message to the Planner Agent. The Planner Agent creates an itinerary and sends a `validate_itinerary` message to the Validator Agent.

The Validator Agent evaluates the itinerary against budget constraints and either:

- Sends `approve_plan` to the orchestrator when the itinerary meets the requirements.
- Sends `request_revision` to the Planner Agent when the itinerary exceeds the permitted budget.

Revision messages preserve the original destination, budget, and trip duration. A maximum iteration limit prevents unsuccessful revision loops from continuing indefinitely.

## Expected Output

With the default three-day Brisbane request and $1,200 budget, the Planner Agent produces an illustrative itinerary costing $500 AUD. The Validator Agent approves it.

Expected result:

- Status: `success`
- Iterations: `3`
- Validation status: `approved`
- Estimated itinerary cost: `$500 AUD`

The system also records message exchanges in the `logs` folder.

## Guardrails and Limitations

Pydantic validates the outer message structure and intent. Detailed itinerary content is validated by the Validator Agent, which checks nonnegative costs, total cost consistency, and maximum budget constraints.

The orchestrator validates receiver identifiers, applies per-agent execution timeouts, enforces maximum iterations, and logs errors.

A timed-out worker thread cannot be forcibly terminated in Python. The orchestrator returns a timeout failure promptly, but the underlying thread may continue running. Separate processes could provide stronger execution control.

The current Planner Agent uses predefined Brisbane itinerary steps rather than generating destination-specific recommendations using a live AI model. Budgets below $400 cannot be satisfied by the current fixed revision strategy.

## Testing

The project includes six automated unit tests:

1. Successful workflow execution.
2. Revision preserving destination information.
3. Unaffordable budget reaching the iteration limit.
4. Invalid receiver handling.
5. Invalid input handling.
6. Agent timeout handling.

Run all tests using:

```bash
python -m unittest -v test_agents.py or py -m unittest -v test_agents.py
```

## Future Improvements

Future improvements could include integration with a live language model, dynamic itinerary generation, improved budget optimisation, and additional agent communication tests.
