# StoreOps API Testing Guide

This document is a self-contained reference for running StoreOps locally
and exercising every API endpoint through the OpenAPI (Swagger) UI or
`curl`. Read top to bottom and you should understand what the application
does, how its five modules fit together, and what each endpoint is for --
you shouldn't need to open the source code to test it.

## 1. What StoreOps is

StoreOps is a retail **store operations management** REST API. It lets a
store team:

- track day-to-day **activities** (restocking runs, planogram resets,
  compliance checks, audits, general tasks),
- organise **programmes** (seasonal rollouts, compliance drives, store
  refits) and assign staff to them,
- look up **staff** (read-only from the outside -- see below),
- receive in-app **alerts** when something operationally relevant happens
  (a staff member is added to a programme, a batch of tasks changes
  status), and
- (in a later iteration) generate **reports** rolling up activity across
  a store or region -- not exposed over HTTP yet in this build.

It is a five-module system (`activities`, `programmes`, `staff`,
`alerts`, `reports`), each following the same internal shape --
`Routes -> Service -> Repository` -- so that HTTP handling, business
rules, and storage stay separated. The one thing worth knowing before you
start clicking around: **when an action in one module needs to notify
another module, it never calls that module directly** -- it fires an
event on an internal event bus, and the other module reacts to it. You'll
see this in practice below: adding a staff member to a programme, or
bulk-updating activity statuses, both quietly create entries in `alerts`
that you can go check with `GET /api/alerts`.

All data is **in-memory** -- nothing persists across a server restart,
except the three demo staff accounts, which are re-seeded every time the
app starts (see Section 3).

---

## 2. Starting the app

### Windows

From the repository root, in a terminal (PowerShell, Command Prompt, or
Git Bash all work):

```bat
start.bat
```

This will, in order: create a `.venv` virtual environment if one doesn't
already exist, install/update all dependencies, start the API on
`http://127.0.0.1:8010`, wait for it to report healthy, and then open the
Swagger UI in your default browser automatically. Leave the window open
-- the server runs in it. Press **Ctrl+C** in that window to stop it, or
run `stop.bat` from another window at any time to force-stop whatever is
currently listening on the port. `start.bat` also self-heals: if a
previous run wasn't shut down cleanly and left a stale process still
bound to the port, it detects and stops that first, so you'll never hit
`WinError 10048: only one usage of each socket address ...` on the next
run.

### macOS / Linux / Git Bash

```bash
./start.sh
```

(If it's not already executable: `chmod +x start.sh stop.sh scripts/wait_and_open.sh` once, then run it.)

Same behaviour as `start.bat`, including the self-heal and the `stop.sh`
companion script: creates/reuses `.venv`, installs dependencies, starts
the server on port 8010, waits for `/health`, and opens the Swagger UI in
your default browser. **Ctrl+C** stops it.

### Manual start (either OS, if you'd rather not use the scripts)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
uvicorn app.main:app --host 127.0.0.1 --port 8010
```

Then open `http://127.0.0.1:8010/docs` yourself.

### Where things are once it's running

| What | URL |
|---|---|
| Swagger UI (interactive docs -- this is the "OpenAPI web UI") | `http://127.0.0.1:8010/docs` |
| Raw OpenAPI schema (JSON) | `http://127.0.0.1:8010/openapi.json` |
| Alternate docs UI (ReDoc, read-only) | `http://127.0.0.1:8010/redoc` |
| Health check | `http://127.0.0.1:8010/health` |

---

## 3. Authorization

Eight of the eleven endpoints below require a bearer token. There is no
real login flow in this build -- three demo staff accounts are seeded
into memory every time the app starts:

| Token (paste exactly this) | Staff member | Role | Store |
|---|---|---|---|
| `demo-store-manager-token` | Priya Shah (`user-store-manager`) | `STORE_MANAGER` | `store-1` |
| `demo-dept-lead-token` | Marcus Webb (`user-dept-lead`) | `DEPARTMENT_LEAD` | `store-1` |
| `demo-associate-token` | Jamie Ortiz (`user-associate`) | `ASSOCIATE` | `store-1` |

The role matters for one rule: **deleting an activity** is only allowed
for the activity's own owner, or for a `STORE_MANAGER` /
`REGIONAL_MANAGER`. Every other authorized action works the same
regardless of which of the three tokens you use.

### In the Swagger UI (`/docs`)

1. Click the green **Authorize** button near the top-right of the page
   (it has a padlock icon).
2. In the "Value" field, paste **just the raw token** -- no `Bearer `
   prefix, no quotes:
   ```
   demo-store-manager-token
   ```
3. Click **Authorize**, then **Close**.
4. You're done for the whole session. Every endpoint that needs auth
   shows a small closed-padlock icon next to its name; you don't fill in
   an `authorization` field per request.

If you don't see the Authorize button, hard-refresh the page
(Ctrl+Shift+R) -- your browser may be showing a cached copy of the
schema from before authorization was wired up.

### Via `curl`

Add the header exactly like this on every call to a protected endpoint:

```bash
curl -H "Authorization: Bearer demo-store-manager-token" http://127.0.0.1:8010/api/programmes
```

### What happens if you don't authorize

Any protected endpoint called without a valid token returns:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing or malformed Authorization header",
    "details": {}
  }
}
```
with HTTP status `401`.

### The error envelope, in general

Every error StoreOps returns on purpose (never a raw framework 500)
follows the same shape:

```json
{
  "error": {
    "code": "<SHORT_MACHINE_CODE>",
    "message": "<human-readable explanation>",
    "details": { "...": "context-specific, e.g. the offending field" }
  }
}
```

| `code` | HTTP status | Meaning |
|---|---|---|
| `NOT_FOUND` | 404 | The id in the URL/body doesn't exist |
| `VALIDATION_ERROR` | 422 | The request is well-formed JSON but breaks a business rule (e.g. `assignee_id` isn't a real staff member) |
| `CONFLICT` | 409 | The action conflicts with current state (e.g. adding a staff member who's already on the programme) |
| `FORBIDDEN` | 403 | Authenticated, but not allowed to do this specific thing |
| `UNAUTHORIZED` | 401 | Missing or invalid bearer token |

---

## 4. Endpoint reference (quick index)

| Method | Path | Auth? | Purpose |
|---|---|---|---|
| GET | `/health` | No | Liveness check |
| GET | `/api/activities` | No | List activities, optionally filtered |
| POST | `/api/activities` | **Yes** | Create an activity |
| GET | `/api/activities/{task_id}` | No | Get one activity by id |
| PATCH | `/api/activities/{task_id}` | **Yes** | Update one activity's fields |
| PATCH | `/api/activities/bulk-status` | **Yes** | Bulk mark activities DONE/BLOCKED |
| DELETE | `/api/activities/{task_id}` | **Yes** | Delete an activity (owner/manager only) |
| GET | `/api/programmes` | **Yes** | List programmes for your store |
| POST | `/api/programmes` | **Yes** | Create a programme |
| POST | `/api/programmes/{programme_id}/members` | **Yes** | Add a staff member to a programme |
| GET | `/api/alerts` | **Yes** | List your own in-app notifications |

Full detail on each, with sample requests and responses, follows.

---

## 5. `GET /health`

**What it's for:** a plain liveness probe -- used by `start.bat`/`start.sh`
to know when the server is ready. No business meaning beyond "the process
is up."

**Auth:** none.

**Sample request**
```bash
curl http://127.0.0.1:8010/health
```

**Sample response** -- `200 OK`
```json
{ "status": "ok" }
```

---

## 6. `GET /api/activities`

**What it's for:** lists activities (tasks) -- the day-to-day work items
a store team tracks: restocking runs, planogram resets, audits,
compliance checks, general tasks. Optionally narrow the list by programme
or status.

**Auth:** none.

**Query parameters** (both optional)

| Name | Type | Example | Meaning |
|---|---|---|---|
| `programme_id` | string | `prog-123` | Only tasks linked to this programme |
| `status` | one of `TODO`, `IN_PROGRESS`, `DONE`, `BLOCKED` | `DONE` | Only tasks currently in this status |

**Sample request**
```bash
curl "http://127.0.0.1:8010/api/activities?status=TODO"
```

**Sample response** -- `200 OK`
```json
[
  {
    "id": "1dcff2b0faa1473e93834693c8dac70e",
    "store_id": "store-1",
    "programme_id": null,
    "title": "Restock aisle 4",
    "description": null,
    "status": "TODO",
    "priority": "MEDIUM",
    "category": "GENERAL",
    "assignee_id": null,
    "owner_id": "user-associate",
    "created_at": "2026-09-11T23:01:56.465769Z",
    "updated_at": "2026-09-11T23:01:56.465769Z"
  }
]
```

---

## 7. `POST /api/activities`

**What it's for:** creates a new activity, owned by whichever staff
member's token you authorized with. This is how new restocking runs,
compliance checks, etc. enter the system.

**Auth:** required. The authenticated user becomes the activity's
`owner_id` and its `store_id` is taken from that user's store.

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `title` | string | yes | |
| `description` | string \| null | no | |
| `programme_id` | string \| null | no | Not validated against a real programme in this build -- any string is accepted |
| `priority` | `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` | no | Defaults to `MEDIUM` |
| `category` | `RESTOCKING` \| `PLANOGRAM` \| `AUDIT` \| `COMPLIANCE` \| `GENERAL` | no | Defaults to `GENERAL` |
| `assignee_id` | string \| null | no | **Is** validated -- must be a real staff id (see Section 3's token table) or the request is rejected |

**Sample request**
```bash
curl -X POST http://127.0.0.1:8010/api/activities \
  -H "Authorization: Bearer demo-associate-token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Restock aisle 4",
    "priority": "MEDIUM",
    "category": "RESTOCKING"
  }'
```

**Sample response** -- `201 Created`
```json
{
  "id": "1dcff2b0faa1473e93834693c8dac70e",
  "store_id": "store-1",
  "programme_id": null,
  "title": "Restock aisle 4",
  "description": null,
  "status": "TODO",
  "priority": "MEDIUM",
  "category": "RESTOCKING",
  "assignee_id": null,
  "owner_id": "user-associate",
  "created_at": "2026-09-11T23:01:56.465769Z",
  "updated_at": "2026-09-11T23:01:56.465769Z"
}
```

**Common error** -- an `assignee_id` that isn't a real staff member:
`422 VALIDATION_ERROR`, `details: {"assignee_id": "1"}`. Use one of the
three seeded ids from Section 3 (or omit the field).

---

## 8. `GET /api/activities/{task_id}`

**What it's for:** fetch one activity by its id -- e.g. to confirm a
status change actually persisted after a `PATCH`.

**Auth:** none.

**Sample request**
```bash
curl http://127.0.0.1:8010/api/activities/1dcff2b0faa1473e93834693c8dac70e
```

**Sample response** -- `200 OK`: same shape as the create response above.

**Error** -- unknown id: `404 NOT_FOUND`:
```json
{ "error": { "code": "NOT_FOUND", "message": "Activity not found", "details": { "id": "does-not-exist" } } }
```

---

## 9. `PATCH /api/activities/{task_id}`

**What it's for:** update one or more fields on an existing activity --
typically moving it through its workflow (`TODO` -> `IN_PROGRESS` ->
`DONE`), reprioritising it, recategorising it, or reassigning it. Only
the fields you include are changed; everything else is left as-is.

**Auth:** required. (No additional ownership check beyond holding a
valid token -- any authenticated user may update any activity via this
endpoint, unlike `DELETE`.)

**Request body** (all fields optional -- send only what you want to
change)

| Field | Type |
|---|---|
| `status` | `TODO` \| `IN_PROGRESS` \| `DONE` \| `BLOCKED` |
| `priority` | `LOW` \| `MEDIUM` \| `HIGH` \| `CRITICAL` |
| `category` | `RESTOCKING` \| `PLANOGRAM` \| `AUDIT` \| `COMPLIANCE` \| `GENERAL` |
| `assignee_id` | string \| null (validated against real staff ids, same as create) |

**Sample request**
```bash
curl -X PATCH http://127.0.0.1:8010/api/activities/1dcff2b0faa1473e93834693c8dac70e \
  -H "Authorization: Bearer demo-associate-token" \
  -H "Content-Type: application/json" \
  -d '{ "status": "DONE" }'
```

**Sample response** -- `200 OK`: full updated activity, with `status`
now `"DONE"` and `updated_at` refreshed.

---

## 10. `PATCH /api/activities/bulk-status`

**What it's for:** the "shift handover" workflow -- an outgoing shift
worker marks a whole batch of activities `DONE` or `BLOCKED` in one call
instead of one `PATCH` per task. If some ids in the batch don't exist,
the valid ones still get updated and the bad ones come back as a
per-item failure list -- the whole request never aborts because one id
was wrong.

This is also the endpoint that demonstrates the event-bus wiring
described in Section 1: **every task that's successfully updated causes
a `SHIFT_HANDOVER` notification to appear in that task's owner's alerts**
(see `GET /api/alerts` below) -- but no notification is created for ids
that failed.

**Auth:** required.

**Request body**

```json
{
  "updates": [
    { "task_id": "<id>", "status": "DONE" },
    { "task_id": "<id>", "status": "BLOCKED" }
  ]
}
```
`status` in each item must be `DONE` or `BLOCKED` (not any other
`TaskStatus` value). `updates` must contain at least one item.

**Sample request** (two real ids, plus one that doesn't exist)
```bash
curl -X PATCH http://127.0.0.1:8010/api/activities/bulk-status \
  -H "Authorization: Bearer demo-store-manager-token" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": [
      { "task_id": "1dcff2b0faa1473e93834693c8dac70e", "status": "DONE" },
      { "task_id": "ae8a10ab29c446ba9f1dacaef8faa6fb", "status": "BLOCKED" },
      { "task_id": "ghost-task", "status": "DONE" }
    ]
  }'
```

**Sample response** -- `200 OK` (note: this always returns 200, even
with partial failures -- check the `failures` array, not the status code)
```json
{
  "updated": [
    { "id": "1dcff2b0faa1473e93834693c8dac70e", "status": "DONE", "...": "..." },
    { "id": "ae8a10ab29c446ba9f1dacaef8faa6fb", "status": "BLOCKED", "...": "..." }
  ],
  "failures": [
    { "task_id": "ghost-task", "code": "NOT_FOUND", "message": "Activity not found" }
  ]
}
```

**Error** -- empty `updates` list: `422 VALIDATION_ERROR`.

---

## 11. `DELETE /api/activities/{task_id}`

**What it's for:** permanently removes an activity. Deliberately
restricted so a random associate can't delete someone else's work.

**Auth:** required, **and** the authenticated user must be either the
activity's `owner_id`, or hold the `STORE_MANAGER`/`REGIONAL_MANAGER`
role.

**Sample request (allowed -- store manager deleting anyone's task)**
```bash
curl -X DELETE http://127.0.0.1:8010/api/activities/1dcff2b0faa1473e93834693c8dac70e \
  -H "Authorization: Bearer demo-store-manager-token"
```

**Sample response** -- `204 No Content` (empty body).

**Sample request (rejected -- a different associate, not the owner)**
```bash
curl -X DELETE http://127.0.0.1:8010/api/activities/1dcff2b0faa1473e93834693c8dac70e \
  -H "Authorization: Bearer demo-dept-lead-token"
```

**Sample response** -- `403 FORBIDDEN`
```json
{
  "error": {
    "code": "FORBIDDEN",
    "message": "Only the activity's owner or a store manager may delete it",
    "details": { "task_id": "1dcff2b0faa1473e93834693c8dac70e", "requester_id": "user-dept-lead" }
  }
}
```

---

## 12. `GET /api/programmes`

**What it's for:** lists the programmes (seasonal rollouts, compliance
drives, store refits) belonging to *your* store -- i.e. the store of
whichever token you authorized with.

**Auth:** required.

**Sample request**
```bash
curl http://127.0.0.1:8010/api/programmes -H "Authorization: Bearer demo-store-manager-token"
```

**Sample response** -- `200 OK`
```json
[
  {
    "id": "9b1e...",
    "store_id": "store-1",
    "name": "Spring Rollout",
    "description": null,
    "members": [],
    "created_at": "2026-09-11T20:00:00Z",
    "updated_at": "2026-09-11T20:00:00Z"
  }
]
```

---

## 13. `POST /api/programmes`

**What it's for:** creates a new programme, owned by your store.

**Auth:** required.

**Request body**

| Field | Type | Required |
|---|---|---|
| `name` | string | yes |
| `description` | string \| null | no |

**Sample request**
```bash
curl -X POST http://127.0.0.1:8010/api/programmes \
  -H "Authorization: Bearer demo-store-manager-token" \
  -H "Content-Type: application/json" \
  -d '{ "name": "Spring Rollout" }'
```

**Sample response** -- `201 Created`
```json
{
  "id": "9b1e1c2f3a4b4c5d6e7f8a9b0c1d2e3f",
  "store_id": "store-1",
  "name": "Spring Rollout",
  "description": null,
  "members": [],
  "created_at": "2026-09-11T20:00:00Z",
  "updated_at": "2026-09-11T20:00:00Z"
}
```

---

## 14. `POST /api/programmes/{programme_id}/members`

**What it's for:** adds a staff member to a programme. This is the
other place the event bus fires: successfully adding a member creates a
`SHIFT_HANDOVER` notification for that member in `GET /api/alerts`,
without `programmes` ever calling `alerts` directly (see Section 1).

**Auth:** required. (No additional restriction beyond holding a valid
token -- any authenticated user may add a member to any programme in
this build.)

**Request body**

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | string | yes | Must be a real staff id (Section 3's table) |
| `role` | `STORE_MANAGER` \| `DEPARTMENT_LEAD` \| `ASSOCIATE` | no | Defaults to `ASSOCIATE`. This is the member's role *within this programme*, independent of their overall staff role |

**Sample request**
```bash
curl -X POST http://127.0.0.1:8010/api/programmes/9b1e1c2f3a4b4c5d6e7f8a9b0c1d2e3f/members \
  -H "Authorization: Bearer demo-store-manager-token" \
  -H "Content-Type: application/json" \
  -d '{ "user_id": "user-associate", "role": "ASSOCIATE" }'
```

**Sample response** -- `201 Created`
```json
{
  "id": "9b1e1c2f3a4b4c5d6e7f8a9b0c1d2e3f",
  "store_id": "store-1",
  "name": "Spring Rollout",
  "description": null,
  "members": [ { "user_id": "user-associate", "role": "ASSOCIATE" } ],
  "created_at": "2026-09-11T20:00:00Z",
  "updated_at": "2026-09-11T20:05:00Z"
}
```

**Errors:** `422 VALIDATION_ERROR` if `user_id` isn't a real staff
member; `409 CONFLICT` if that member is already on the programme;
`404 NOT_FOUND` if `programme_id` doesn't exist.

---

## 15. `GET /api/alerts`

**What it's for:** lists in-app notifications addressed to *you* (the
authenticated user) -- this is where you see the audit-trail side
effects from Sections 10 and 14 land. Nothing writes here directly from
another module; every notification you see arrived via the event bus.

**Auth:** required.

**Sample request**
```bash
curl http://127.0.0.1:8010/api/alerts -H "Authorization: Bearer demo-associate-token"
```

**Sample response** -- `200 OK`
```json
[
  {
    "id": "bcd24aa6de6a497f809c42bbde8fd9c9",
    "user_id": "user-associate",
    "channel": "IN_APP",
    "type": "SHIFT_HANDOVER",
    "message": "Task '1dcff2b0faa1473e93834693c8dac70e' status changed to 'DONE'.",
    "status": "UNREAD",
    "source_module": "activities",
    "created_at": "2026-09-11T23:01:59.567792Z"
  }
]
```

`type` will be one of `INVENTORY`, `SLA_BREACH`, `SHIFT_HANDOVER`,
`ESCALATION` (only `SHIFT_HANDOVER` is actually produced by the current
baseline). `source_module` tells you which module's event caused this
notification -- currently always `"activities"` or `"programmes"`.

---

## 16. A worked end-to-end walkthrough

Ties every endpoint above into one coherent scenario -- run these in
order (all against `http://127.0.0.1:8010`, all `-H "Content-Type:
application/json"` on POST/PATCH):

1. **Create a programme** as the store manager:
   `POST /api/programmes {"name": "Spring Rollout"}` -> note the `id`.
2. **Add an associate to it** (as the store manager -- this endpoint
   requires auth, though not specifically the *store manager's* auth):
   `POST /api/programmes/<id>/members {"user_id": "user-associate"}`.
3. **Check their alerts** -- a `SHIFT_HANDOVER` notification should
   already be there: `GET /api/alerts` with the associate's token.
4. **Create two activities** as the associate:
   `POST /api/activities {"title": "Restock aisle 4"}` (twice) -> note
   both `id`s.
5. **Bulk-close them** (plus one fake id) as the store manager:
   `PATCH /api/activities/bulk-status` with both real ids set to `DONE`
   and one made-up id.
6. **Confirm the state changed:** `GET /api/activities/<id>` for each ->
   `status` is now `"DONE"`.
7. **Confirm the audit trail:** `GET /api/alerts` for the associate again
   -- two more `SHIFT_HANDOVER` notifications, one per real task, and
   nothing referencing the fake id.
8. **Try deleting one as a non-owner, non-manager** (`demo-dept-lead-token`)
   -> `403 FORBIDDEN`, task still exists. Then delete it as the store
   manager -> `204 No Content`, and a follow-up `GET` on that id now
   returns `404 NOT_FOUND`.

If all eight steps behave as described, every module and the event-bus
wiring between them are working end-to-end.
