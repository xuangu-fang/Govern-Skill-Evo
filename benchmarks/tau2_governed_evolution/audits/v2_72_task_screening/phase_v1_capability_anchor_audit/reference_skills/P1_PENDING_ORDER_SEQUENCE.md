# Pending-order multi-mutation sequencing

When one pending order needs an item change plus other order-level changes, inspect and plan the complete request before committing anything. An item-change action is terminal for further modifications to that order, so complete any requested whole-order payment and address changes first and perform the item change last. Use the user's specified payment method for any item price difference. Preserve every unrequested field, obtain the required confirmation, and do not retry an ineligible write after the item mutation.
