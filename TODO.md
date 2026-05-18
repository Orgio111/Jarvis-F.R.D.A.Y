# TODO

- [ ] Update Go gateway routing so `GET /api/bootstrap` is exempt from `mw.Session` (X-Session-ID required), while keeping `mw.Session` for all protected feature routes.
- [ ] Build/test Go gateway to ensure compilation and route wiring correctness.
