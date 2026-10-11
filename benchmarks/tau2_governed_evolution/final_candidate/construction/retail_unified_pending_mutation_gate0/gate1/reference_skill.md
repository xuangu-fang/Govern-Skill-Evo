# Pending-order multi-mutation sequencing

For one pending order that needs both a whole-order payment replacement and an
item change, inspect and confirm the complete final-state request before any
write. Replace the whole-order payment first, complete any requested shipping
address update next, and mutate items last. Use the user's specified new
payment method for any item price difference. Preserve unrequested fields and
do not retry an ineligible write after the item mutation.
