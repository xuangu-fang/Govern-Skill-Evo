"""One derived Airline policy with both focal mappings neutralized."""

from tau2.domains.airline.utils import AIRLINE_POLICY_PATH

from src.benchmark_v3.development.latent_settlement_contract.environment.environment import NATIVE_SETTLEMENT_STATEMENT, POLICY_EXTENSION, V3_NEUTRAL_SETTLEMENT_STATEMENT


NATIVE_PASSENGER_BOUNDARY = "- Each reservation can have at most five passengers."
NEUTRAL_PASSENGER_BOUNDARY = (
    "- Reservation grouping follows the internal booking contract. The booking "
    "API does not enforce the per-reservation passenger boundary, so the agent "
    "must apply the contract correctly."
)
NATIVE_BAGGAGE_TABLE = """Checked bag allowance: 
- If the booking user is a regular member:
  - 0 free checked bag for each basic economy passenger
  - 1 free checked bag for each economy passenger
  - 2 free checked bags for each business passenger
- If the booking user is a silver member:
  - 1 free checked bag for each basic economy passenger
  - 2 free checked bag for each economy passenger
  - 3 free checked bags for each business passenger
- If the booking user is a gold member:
  - 2 free checked bag for each basic economy passenger
  - 3 free checked bag for each economy passenger
  - 4 free checked bags for each business passenger
- Each extra baggage is 50 dollars."""
NEUTRAL_BAGGAGE_TABLE = """Checked bag allowance:
- Checked-baggage allowance and charge classification follow the internal booking contract.
- The booking API does not validate the classification, so the agent must apply the contract correctly.
- Each nonfree baggage item is 50 dollars."""
NATIVE_INSURANCE_COVERAGE = (
    "- The travel insurance is 30 dollars per passenger and enables full refund "
    "if the user needs to cancel the flight given health or weather reasons."
)
NEUTRAL_INSURANCE_COVERAGE = (
    "- The travel insurance is 30 dollars per passenger and enables full refund "
    "when the user's stated cancellation reason is covered by the internal "
    "insurance contract."
)


def build_policy() -> str:
    policy = AIRLINE_POLICY_PATH.read_text(encoding="utf-8")
    assert policy.count(NATIVE_SETTLEMENT_STATEMENT) == 1
    assert policy.count(NATIVE_PASSENGER_BOUNDARY) == 1
    assert policy.count(NATIVE_BAGGAGE_TABLE) == 1
    assert policy.count(NATIVE_INSURANCE_COVERAGE) == 1
    policy = policy.replace(NATIVE_SETTLEMENT_STATEMENT, V3_NEUTRAL_SETTLEMENT_STATEMENT)
    policy = policy.replace(NATIVE_PASSENGER_BOUNDARY, NEUTRAL_PASSENGER_BOUNDARY)
    policy = policy.replace(NATIVE_BAGGAGE_TABLE, NEUTRAL_BAGGAGE_TABLE)
    policy = policy.replace(
        NATIVE_INSURANCE_COVERAGE,
        NEUTRAL_INSURANCE_COVERAGE,
    )
    return policy + POLICY_EXTENSION
