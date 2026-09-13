---
name: app-context
description: The StoreOps retail-operations glossary -- five modules, their entities, enums, and who owns what. Read before touching any module.
---

# StoreOps app context

StoreOps is a retail store operations management REST API. It has five
modules under `src/app/modules/`, each owning its own `models.py`,
`repository.py`, `service.py`, and (except `staff` and `reports`, see
below) `routes.py`.

## activities (`src/app/modules/activities/`)

Operational activities: restocking runs, planogram resets, compliance
checks, general tasks.

- `Task` -- `id`, `store_id`, `programme_id` (optional link to a
  `programmes.Project`), `title`, `description`, `status`, `priority`,
  `category`, `assignee_id`, `owner_id`, `created_at`, `updated_at`.
- `TaskStatus`: `TODO | IN_PROGRESS | DONE | BLOCKED`
- `TaskPriority`: `LOW | MEDIUM | HIGH | CRITICAL`
- `TaskCategory`: `RESTOCKING | PLANOGRAM | AUDIT | COMPLIANCE | GENERAL`

Owns the `/api/activities` endpoints (list, create, get, patch, delete).
Delete is owner-or-store-manager only (`ForbiddenError` otherwise).

## programmes (`src/app/modules/programmes/`)

Store programmes and their staff membership: seasonal rollouts,
compliance drives, store refits.

- `Project` -- `id`, `store_id`, `name`, `description`, `members`
  (`list[ProjectMember]`), `created_at`, `updated_at`.
- `ProjectMember` -- `user_id`, `role`.
- `ProjectRole`: `STORE_MANAGER | DEPARTMENT_LEAD | ASSOCIATE`

Owns `/api/programmes` (list, create) and
`/api/programmes/{id}/members` (add member). Adding a member fires
`programme.member_added` on the event bus -- see `component-patterns`.

## staff (`src/app/modules/staff/`)

Store staff identity and auth. **Read-only for every other module** --
`activities`, `programmes`, `alerts`, and `reports` all read staff data
through `staff_service`, never `staff.repository`.

- `User` -- `id`, `store_id`, `name`, `email`, `staff_role`, `profile`.
- `UserProfile` -- `phone`, `bio` (optional detail, nested in `User`).
- `StaffRole`: `REGIONAL_MANAGER | STORE_MANAGER | DEPARTMENT_LEAD |
  ASSOCIATE`
- `AuthToken` -- `token`, `user_id`.

No public routes -- `staff` has no CRUD surface in the base API (matches
Section 3.6 of the capstone spec). Auth is a fake bearer-token scheme:
`core/auth.py`'s `get_current_user` resolves `Authorization: Bearer
<token>` against three seeded demo users/tokens (see
`staff/repository.py`'s `_seed_demo_data`), all in `store-1`:

| Token | User | Role |
|---|---|---|
| `demo-store-manager-token` | `user-store-manager` (Priya Shah) | `STORE_MANAGER` |
| `demo-dept-lead-token` | `user-dept-lead` (Marcus Webb) | `DEPARTMENT_LEAD` |
| `demo-associate-token` | `user-associate` (Jamie Ortiz) | `ASSOCIATE` |

## alerts (`src/app/modules/alerts/`)

In-app notifications triggered by operational events.

- `Notification` -- `id`, `user_id`, `channel`, `type`, `message`,
  `status`, `source_module`, `created_at`.
- `NotificationChannel`: `IN_APP | EMAIL`
- `NotificationType`: `INVENTORY | SLA_BREACH | SHIFT_HANDOVER |
  ESCALATION`
- `NotificationStatus`: `UNREAD | READ`

Owns `/api/alerts` (list for the authenticated user). Also the
**subscriber side** of the one cross-module event wired up so far:
`alert_service.handle_programme_member_added` reacts to
`programme.member_added`.

## reports (`src/app/modules/reports/`)

Store and regional performance summaries. **Read-only across every other
module** -- aggregates via `activities.service` and `programmes.service`,
never writes to them.

- `Report` -- `id`, `type`, `status`, `store_id`, `payload` (dict),
  `created_at`.
- `ReportType`: `STORE_SUMMARY | REGIONAL_ROLLUP |
  DEPARTMENT_PERFORMANCE`
- `ReportStatus`: `PENDING | READY | FAILED`

No public routes in the baseline -- Section 3.6's base API surface does
not include a reports endpoint; `reports` exists and is tested (see
`build_store_summary`) so the layer is in place the moment a reporting
feature is actually requested through the harness.

## Shared infrastructure (`src/app/core/`)

- `errors.py` -- the `AppError` hierarchy (see `component-patterns`).
- `event_bus.py` -- the in-memory `EventBus` (see `component-patterns`).
- `repository.py` -- `InMemoryRepository[T]`, the generic thread-safe
  store every module's own repository wraps.
- `auth.py` -- `get_current_user`, the fake bearer-token dependency.

All storage is in-memory, process-lifetime only -- there is no database in
this capstone reference app.
