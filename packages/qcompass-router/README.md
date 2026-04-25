# qcompass-router

Routing layer for QCompass: provider adapters and a routing policy that picks
the cheapest viable backend for a circuit + budget + fidelity request.

This is the Phase-6A skeleton (provider adapters + baseline routing).
Phase-6B fills in production pricing, calibration drift, transforms, and the
full audit suite.

## Layout

- `src/qcompass_router/router.py` — `Router.decide(BackendRequest)`
- `src/qcompass_router/decision.py` — `BackendRequest`, `RoutingDecision`
- `src/qcompass_router/budget.py` — `UserBudget`, `ProjectBudget`
- `src/qcompass_router/pricing_stub.py` — static pricing lookup (Phase-6A)
- `src/qcompass_router/providers/` — one file per provider, soft-imported

All provider SDK imports are guarded inside `is_available()` so the package
imports cleanly in environments where no provider SDK is installed.
