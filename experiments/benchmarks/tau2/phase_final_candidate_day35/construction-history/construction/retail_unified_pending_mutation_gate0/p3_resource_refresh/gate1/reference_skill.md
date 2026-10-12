# Refresh shared payment resources after writes

When one requested order mutation can refund or otherwise change a stored-value
payment resource needed by a later request, do not retain a feasibility decision
made from the initial balance. Complete the upstream mutation, re-read the
user's payment methods, calculate from the refreshed balance, and then complete
the downstream request if it is feasible. Preserve unrelated state and obtain
the normal confirmation for every write.
