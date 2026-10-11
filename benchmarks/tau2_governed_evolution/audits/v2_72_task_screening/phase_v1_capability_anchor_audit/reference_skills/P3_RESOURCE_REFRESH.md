# Mutation-induced resource refresh

When an earlier requested mutation can refund money to or otherwise change a stored-value payment resource needed by a later request, do not decide downstream feasibility from its initial balance. Complete the upstream mutation first, refresh the user/payment state, calculate with the resulting balance, and then carry out the downstream request if feasible. Preserve all unrelated fields and follow the normal confirmation requirements for each operation.
