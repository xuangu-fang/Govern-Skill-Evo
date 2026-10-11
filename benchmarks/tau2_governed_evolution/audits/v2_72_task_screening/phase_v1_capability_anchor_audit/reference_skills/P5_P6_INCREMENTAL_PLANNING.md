# Incremental reservation planning and propagation

For a reservation modification, compare each candidate by the transaction's incremental charge or refund relative to the current preserved reservation, not by the candidate's gross itinerary price. Resolve all dependent branches—including cabin, baggage, passengers, budget, and preserved segments—before the first write. Present the complete selected package and exact consequence for confirmation, then apply only the required mutations while preserving every invariant the user did not ask to change.
