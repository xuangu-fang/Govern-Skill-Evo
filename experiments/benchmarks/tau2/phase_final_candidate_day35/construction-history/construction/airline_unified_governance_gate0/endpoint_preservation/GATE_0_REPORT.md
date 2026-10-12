# Endpoint Preservation zero-model Gate 0

Result: `PASS_ENDPOINT_PRESERVATION_ZERO_MODEL_GATE_0`

The shared attempt-level rule
`airline.flight_change.endpoint_preservation.v1` is implemented in an explicit
construction evidence profile. It is not active in the default v1 registry.

Both required topology matrices passed:

| Topology | Legal path | Competing path |
|---|---|---|
| `DIRECT_THIRD_CITY_ENDPOINT_REPLACEMENT` | separate booking → CS | endpoint-changing update → VS |
| `APPENDED_REVERSE_RETURN` | separate return booking → CS | append reverse leg to existing reservation → VS |

The rule also passed same-endpoint direct and connection controls, indirect reverse
append, failed violating attempt retention, separate-booking non-applicability, and
UNSCORED handling for unresolved, empty, or discontinuous proposals. Existing
Governance fixtures, P4/P5 checks, and all 32 v3 oracle paths remained unchanged.

Model calls: 0. Formal task IDs: 0.

Machine-readable result: `gate0_validation.json`.
