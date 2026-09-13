/planner Add shift handover bulk update to activities:
PATCH /api/activities/bulk-status lets outgoing shift staff mark
multiple activities DONE or BLOCKED in one request, with partial-failure
handling and an audit entry per updated task.
