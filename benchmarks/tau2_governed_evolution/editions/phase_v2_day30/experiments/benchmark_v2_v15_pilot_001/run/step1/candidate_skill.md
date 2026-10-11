# Operational Skill

## Planning and navigation

- For airline requests, when a user asks to book multiple reservations with a fixed set of stored-value payment methods that includes a travel certificate, plan the payment allocation before executing bookings. Do not reuse a travel certificate across multiple reservations, and avoid spending the travel certificate on an earlier booking when a later booking also needs it. Use a lower-risk saved payment method for the earlier booking when available, reserve the single-use certificate for the later booking, and obtain explicit user confirmation before booking.

## Execution patterns

- For retail requests, when a user asks to cancel all pending orders, return a received item, and learn the total refund amount, authenticate the user by email or name plus zip, fetch user and order details, check order statuses, identify pending orders and the delivered item the user confirms as received, compute the refund total from the pending-order totals plus the delivered item's refund amount, obtain explicit confirmation of the cancellation reason, return item, and refund method, then call cancel_pending_order for each pending order and return_delivered_order_items for only the confirmed delivered item.
- For airline requests, when multiple tool lookups appear necessary before a booking modification, make exactly one tool call per assistant turn and wait for that tool result before making another tool call. Do not send a user-visible message in the same turn as a tool call; use a turn either to ask a question or to make one tool call, then wait.
- For retail requests, when a pending order needs both a whole-order payment method change and one or more item modifications, call modify_pending_order_payment first, wait for its successful result, and then call modify_pending_order_items with the item changes and the new payment method for any price difference. Do not modify items before the payment-method change, and do not issue the item-modification call before the payment-modification result is returned.

## Form entry and verification

- For airline requests, when a user asks to cancel a flight reservation, explicitly ask for the reason for cancellation before proceeding to check eligibility or execute the cancellation. Wait for the user to provide a reason, then continue with eligibility checks and confirmation.
- For retail requests, when a user requests return of one or more delivered-order items, authenticate the user by email or name plus zip, fetch user and order details, verify the order status is delivered, verify the requested item is in the order, verify the refund method is the original payment method or an existing gift card, present the return details, obtain explicit yes confirmation, and only then call return_delivered_order_items. After a successful return, summarize the result and applicable return follow-up.

## Error recovery and stopping

- For airline requests, when a user asks to cancel a reservation for a change-of-plan reason and travel insurance is present, verify eligibility before calling cancel_reservation. Do not treat the mere presence of travel insurance as sufficient; retrieve reservation and flight details, check whether an affirmative cancellation condition is met, such as booking within the last 24 hours, airline-cancelled flight, business class, or a confirmed insurance-covered reason. If no condition is met, deny the cancellation and do not call cancel_reservation.
- For retail requests, when a gift-card payment modification appears underfunded while another already-confirmed balance-affecting action, such as cancelling an order paid with the same gift card, may change that balance, complete the confirmed balance-affecting action first and re-query the user's payment methods before declining. Decline only if the updated balance is still insufficient or the user chooses not to proceed; otherwise obtain explicit confirmation before modifying the payment method.
