# RAP-01: Contract-Conditioned Address Propagation

RAP-01 tests a delayed cross-object overwrite rather than a simple terminal
choice. The customer requests two different final addresses: one for the
current pending order and one for the long-term user profile. Both fields and
both native writes are visible, but the operational meaning of the neutral
contract label is learned from experience.

- `cedar`: a profile write propagates to the pending order, so write profile
  first and order second.
- `orbit`: an order write propagates to the profile, so write order first and
  profile second.

The agent-visible policy says propagation exists but does not disclose this
mapping. Each explicit target can be written once. A wrong sequence therefore
allows both tools to return success, closes the session, and leaves one final
address incorrect.

## Gate criteria

Gate 0 requires four deterministic backend paths, no native-domain changes,
opposite correct sequences under the same request surface order, and one win
out of two for either fixed-order shortcut. Gate 1 uses two tasks, E0/ER, two
repeats, and eight total rollouts. Passing Gate 1 does not itself admit tasks to
the formal benchmark.
