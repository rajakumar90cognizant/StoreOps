# Deployment

## Target: local (native `uvicorn`), not Docker

`Dockerfile` and `docker-compose.yml` are present and configured
identically to the native path (same `pyproject.toml`/`requirements.txt`,
same start command). They were **not** exercised for this submission: this
machine does not have Docker Desktop installed, and enabling it requires
WSL2, which in turn requires local-administrator rights this account does
not have. Rather than fake a container run, this deployment uses the
"Local Docker -- minimum" bar's non-container fallback: the app started
and verified directly via the native venv, which is the same thing the
Dockerfile's `CMD` does (`uvicorn app.main:app --host 0.0.0.0 --port
8000`), just without the container boundary.

If Docker access becomes available, the containerised path is:

```
docker compose up --build
curl http://localhost:8000/api/activities
```

## Steps actually taken

1. Activate the project venv and confirm the baseline gates pass (see
   `.harness/reviews/` for the sprint-by-sprint record):

   ```
   source .venv/Scripts/activate
   mypy . && ruff check . && pytest --cov=src/app --cov-report=json --cov-report=term-missing && python scripts/check_coverage.py
   ```

2. Start the app:

   ```
   uvicorn app.main:app --host 127.0.0.1 --port 8010
   ```

   Log:

   ```
   INFO:     Started server process [19652]
   INFO:     Waiting for application startup.
   INFO:     Application startup complete.
   INFO:     Uvicorn running on http://127.0.0.1:8010 (Press CTRL+C to quit)
   ```

3. Exercise the harness-generated feature end-to-end with real HTTP calls
   (not a unit test -- this is the running application):

   ```bash
   # Create two tasks owned by user-associate
   POST /api/activities {"title": "Restock aisle 4"}   -> id A, status TODO
   POST /api/activities {"title": "Planogram reset"}    -> id B, status TODO

   # Bulk update: A -> DONE, B -> BLOCKED, plus one id that doesn't exist
   PATCH /api/activities/bulk-status
   {"updates": [
     {"task_id": "<A>", "status": "DONE"},
     {"task_id": "<B>", "status": "BLOCKED"},
     {"task_id": "ghost-task", "status": "DONE"}
   ]}
   ```

   Response:

   ```json
   {
     "updated": [
       { "id": "<A>", "status": "DONE",    "...": "..." },
       { "id": "<B>", "status": "BLOCKED", "...": "..." }
     ],
     "failures": [
       { "task_id": "ghost-task", "code": "NOT_FOUND", "message": "Activity not found" }
     ]
   }
   ```

4. Confirmed the state actually changed server-side, not just in the
   PATCH response, by re-fetching both tasks:

   ```
   GET /api/activities/<A>  -> status: "DONE"
   GET /api/activities/<B>  -> status: "BLOCKED"
   ```

5. Confirmed the cross-module event-bus side effect (sprint 2's whole
   point): the task owner's alerts now contain exactly two
   `SHIFT_HANDOVER` audit entries, one per successfully-updated task, and
   **none** referencing the nonexistent `ghost-task`:

   ```
   GET /api/alerts   (as user-associate)
   [
     {"type": "SHIFT_HANDOVER", "message": "Task '<A>' status changed to 'DONE'.", "source_module": "activities", ...},
     {"type": "SHIFT_HANDOVER", "message": "Task '<B>' status changed to 'BLOCKED'.", "source_module": "activities", ...}
   ]
   ```

6. Stopped the server.

This confirms the feature the harness built is real and working in the
running application, not just passing in `pytest`: partial-failure
handling, the typed `NOT_FOUND` failure entry, the state change, and the
`activities -> event_bus -> alerts` audit trail all verified live.
