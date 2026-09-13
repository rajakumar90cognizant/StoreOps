---
name: how-to-test
description: pytest + httpx.AsyncClient fixtures, the exact StoreOps coverage thresholds, and what counts as a state assertion vs. a status-code check. The Generator must follow this for every test it writes.
---

# How to test StoreOps

## Fixtures (`tests/conftest.py`)

- `client` -- an `httpx.AsyncClient` wired to the real ASGI app via
  `ASGITransport(app=app)`. Route tests use this, never `TestClient` or a
  hand-rolled comparison against internals.
- `store_manager_headers` / `dept_lead_headers` / `associate_headers` --
  `{"Authorization": "Bearer <seeded demo token>"}` for the three seeded
  `staff` users (see `app-context`).
- `_reset_state` (autouse) -- clears `activity_repository`,
  `programme_repository`, `alert_repository`, `report_repository` before
  every test. `staff_repository` is deliberately **not** cleared -- its
  seed data is the auth backbone every other fixture depends on.

Route test functions are plain `async def test_...() -> None:` with no
`@pytest.mark.asyncio` decorator needed -- `pyproject.toml` sets
`asyncio_mode = "auto"`.

## Coverage thresholds (enforced by `scripts/check_coverage.py`)

| Layer | Threshold | How it's measured |
|---|---|---|
| Service (`*/service.py`) | >= 80% | per-file average |
| Route (`*/routes.py`) | >= 70% | per-file average |
| Shared (`app/core/*.py`) | >= 60% | per-file average |
| Overall | >= 70% | `coverage.json` project total |

Run:

```
pytest --cov=src/app --cov-report=json --cov-report=term-missing
python scripts/check_coverage.py
```

The script's exit code is the gate -- see `how-to-review` for how the
Evaluator uses it.

## What counts as a state assertion (required) vs. a status-code check (not sufficient alone)

**Not sufficient alone:**

```python
resp = await client.patch(f"/api/activities/{task_id}", json={"status": "DONE"})
assert resp.status_code == 200
```

This proves the endpoint *responded*. It proves nothing about whether the
business rule actually happened.

**Required alongside it -- re-fetch and check the state actually
changed:**

```python
resp = await client.patch(f"/api/activities/{task_id}", json={"status": "DONE"})
assert resp.status_code == 200
assert resp.json()["status"] == "DONE"

get_resp = await client.get(f"/api/activities/{task_id}")
assert get_resp.json()["status"] == "DONE"  # state persisted, not just echoed
```

**Or, for a rejected action, assert the typed error code, not just the
HTTP status:**

```python
resp = await client.delete(f"/api/activities/{task_id}", headers=dept_lead_headers)
assert resp.status_code == 403
assert resp.json()["error"]["code"] == "FORBIDDEN"

still_there = await client.get(f"/api/activities/{task_id}")
assert still_there.status_code == 200  # business rule: nothing was deleted
```

**For an event-bus side effect, assert the effect landed in the
*subscribing* module, not just that the emitting call didn't raise:**

```python
updated = programme_service.add_member(project.id, ProjectMemberCreate(user_id=associate.id))
assert any(m.user_id == associate.id for m in updated.members)

notifications = alert_service.list_for_user(associate.id)
assert any(n.source_module == "programmes" for n in notifications)
```

Any acceptance criterion whose only test is a bare
`resp.status_code == <n>` with no follow-up state check is a Dimension 2
finding in `evaluator-feedback.md`, worded "AC N satisfied by code but not
verified by test" -- see `evaluator.md`.
