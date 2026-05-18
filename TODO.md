# TODO

All previously listed items have been resolved. See git log for details.

## Remaining known gaps (low priority)

- [ ] Chat handler: proxy errors do not yet distinguish `ErrCircuitOpen` from generic 503 — chat uses direct HTTP forwarding, not `aiProxy.Get/Post`. Consider refactoring to use shared transport so circuit breaker covers streaming too.
- [ ] Consider adding `GATEWAY_API_KEY` rotation (dual-key support) for zero-downtime key rotation in production.
