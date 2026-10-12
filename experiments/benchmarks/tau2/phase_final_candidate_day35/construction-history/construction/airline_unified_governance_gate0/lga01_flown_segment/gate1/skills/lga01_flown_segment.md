# Airline cancellation state verification

Before cancelling any reservation, retrieve the reservation and query the
authoritative status of every segment in it. Apply the any-portion-flown guard
before ordinary cancellation grounds such as Business cabin.

If one or more segments have landed while later travel remains available, do not
call the cancellation tool. Explain that the partially travelled reservation
requires human handling and transfer the customer. Do not rely on dates or on a
customer statement as a substitute for checking every segment status.
