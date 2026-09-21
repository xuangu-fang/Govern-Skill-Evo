# Fare-class resource allocation

For a request containing separate Basic Economy and standard Economy bookings,
inspect all requested fare classes and available stored-value resources before
committing either booking.

In this service, a travel certificate is accepted for standard Economy but is
not accepted for Basic Economy. A gift card is accepted for either fare class.
When both resources can cover either fare by amount and both bookings are
required, use the gift card for the Basic Economy booking and preserve the
certificate for the standard Economy booking. Apply this mapping from fare
class, regardless of which booking is cheaper or appears first.

Obtain confirmation for each concrete booking and allocation before writing.
