# Operational Skill

## Planning and navigation

- For retail requests, to cancel a pending order: authenticate the user (e.g., by email), retrieve user and order details, verify the order status is pending, present the order id, cancellation reason, and refund method, obtain explicit user confirmation, then call cancel_pending_order. After cancellation, summarize the result and explain the refund timing based on the original payment method. Do not proceed to cancellation without explicit user confirmation.
- For airline requests, when a user requests cancellation of a specific reservation with a refund, first verify the user account and reservation, confirm the reservation belongs to the user, check that the reason appears valid based on reservation details and the user's statement, state the cancellation action and refund plan, obtain explicit user confirmation, call cancel_reservation only for the intended reservation, and report the refund to the original payment method. Do not cancel other bookings or assert refund eligibility beyond what can be confirmed from the tools and visible policy.

## Execution patterns

- For retail requests, when the assistant has initiated find_user_id_by_email or find_user_id_by_name_zip but not yet received the result, do not call get_order_details or other order-specific tools. Wait until the user_id is returned before accessing any order information or taking order-specific actions.
- For retail requests, when modifying a pending order that requires both a payment method change and item modifications, call modify_pending_order_payment (and modify_pending_order_address if needed) before calling modify_pending_order_items. This avoids a payment history error that occurs when items are modified first and a price-difference refund splits the payment record.
- For airline requests, always make one tool call at a time and wait for the tool result before issuing another call. Do not issue multiple tool calls concurrently or before the previous result has been received.

## Form entry and verification

- For airline requests, before presenting the final booking summary or proceeding to book a flight, explicitly ask the user whether they want to purchase travel insurance, even if the user previously mentioned not needing it. Record the user's yes/no choice and do not infer the answer from prior statements. Proceed only after receiving an explicit choice.
- For airline requests, before calling cancel_reservation, include the cancellation reason as a distinct item in the confirmation summary (e.g., 'Reason for cancellation: Change of plan') and obtain explicit user confirmation. Do not cancel without restating the reason and receiving an explicit yes.
- For airline requests, when preparing a cancellation/refund confirmation, state only the supported action details (such as the reservation id, cancellation action, and refund to the original payment method) and obtain explicit user confirmation. Do not include policy-derived statements like 'travel insurance enables cancellation' or internal refund timelines such as 'refund within 5-7 business days.'

## Error recovery and stopping

