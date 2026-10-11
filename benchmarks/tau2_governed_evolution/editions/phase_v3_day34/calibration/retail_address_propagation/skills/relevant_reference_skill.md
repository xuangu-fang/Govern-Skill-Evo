# RAP-01 Address Synchronization

When a request requires different final addresses for a pending order and the
user profile, authenticate the customer, inspect both objects, collect and
confirm both exact goals, and call `get_address_propagation_context` before the
first write.

Use the contract label to order the two native writes:

- `cedar`: write the profile address first, then write the order address.
- `orbit`: write the order address first, then write the profile address.

Do not reverse or test the sequence. The source-side write propagates to the
other object; after each target has been explicitly written once, the session
closes and an overwritten address cannot be corrected.
