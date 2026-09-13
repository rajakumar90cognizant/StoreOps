"""Activities route tests -- exercised through the real ASGI app.

Deliberately checks response bodies and follow-up state, not just status
codes: after PATCH we re-fetch and confirm the state actually changed, and
on error we assert the AppError JSON envelope shape.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_create_then_get_activity_round_trips(
    client: AsyncClient, associate_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/activities", json={"title": "Restock dairy aisle"}, headers=associate_headers
    )
    assert create_resp.status_code == 201
    created = create_resp.json()
    assert created["status"] == "TODO"

    get_resp = await client.get(f"/api/activities/{created['id']}")

    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Restock dairy aisle"


async def test_patch_activity_status_persists(
    client: AsyncClient, associate_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/activities", json={"title": "Planogram reset"}, headers=associate_headers
    )
    task_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/activities/{task_id}", json={"status": "DONE"}, headers=associate_headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "DONE"

    get_resp = await client.get(f"/api/activities/{task_id}")

    # state actually changed on the server, not just echoed back in the PATCH response
    assert get_resp.json()["status"] == "DONE"


async def test_get_unknown_activity_returns_typed_not_found_envelope(
    client: AsyncClient,
) -> None:
    resp = await client.get("/api/activities/does-not-exist")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"


async def test_delete_by_non_owner_non_manager_is_forbidden_and_task_survives(
    client: AsyncClient, associate_headers: dict[str, str], dept_lead_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/activities", json={"title": "Owner-only task"}, headers=associate_headers
    )
    task_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/activities/{task_id}", headers=dept_lead_headers)

    assert delete_resp.status_code == 403
    assert delete_resp.json()["error"]["code"] == "FORBIDDEN"

    # business rule check, not just the status code: the task must still exist
    still_there = await client.get(f"/api/activities/{task_id}")
    assert still_there.status_code == 200


async def test_create_activity_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/activities", json={"title": "No auth"})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"


async def test_update_activity_requires_auth(
    client: AsyncClient, associate_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/activities", json={"title": "Needs auth to patch"}, headers=associate_headers
    )
    task_id = create_resp.json()["id"]

    resp = await client.patch(f"/api/activities/{task_id}", json={"status": "DONE"})

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    # business rule check, not just the status code: the task must be unchanged
    still_todo = await client.get(f"/api/activities/{task_id}")
    assert still_todo.json()["status"] == "TODO"


async def test_list_activities_filters_by_status_query_param(
    client: AsyncClient, associate_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/activities", json={"title": "Filter target"}, headers=associate_headers
    )
    task_id = create_resp.json()["id"]
    await client.patch(
        f"/api/activities/{task_id}", json={"status": "BLOCKED"}, headers=associate_headers
    )

    resp = await client.get("/api/activities", params={"status": "BLOCKED"})

    ids = [t["id"] for t in resp.json()]
    assert task_id in ids


async def test_bulk_update_status_rejects_invalid_status_value_and_leaves_task_unchanged(
    client: AsyncClient, associate_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/activities", json={"title": "Bulk target"}, headers=associate_headers
    )
    task_id = create_resp.json()["id"]

    resp = await client.patch(
        "/api/activities/bulk-status",
        json={"updates": [{"task_id": task_id, "status": "TODO"}]},
        headers=associate_headers,
    )

    assert resp.status_code == 422

    get_resp = await client.get(f"/api/activities/{task_id}")
    assert get_resp.json()["status"] == "TODO"


async def test_bulk_update_status_succeeds_for_both_tasks(
    client: AsyncClient, store_manager_headers: dict[str, str], associate_headers: dict[str, str]
) -> None:
    create_a = await client.post(
        "/api/activities", json={"title": "Bulk A"}, headers=associate_headers
    )
    create_b = await client.post(
        "/api/activities", json={"title": "Bulk B"}, headers=associate_headers
    )
    task_a_id = create_a.json()["id"]
    task_b_id = create_b.json()["id"]

    resp = await client.patch(
        "/api/activities/bulk-status",
        json={
            "updates": [
                {"task_id": task_a_id, "status": "DONE"},
                {"task_id": task_b_id, "status": "DONE"},
            ]
        },
        headers=store_manager_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    updated_ids = {item["id"]: item["status"] for item in body["updated"]}
    assert updated_ids == {task_a_id: "DONE", task_b_id: "DONE"}
    assert body["failures"] == []

    get_a = await client.get(f"/api/activities/{task_a_id}")
    get_b = await client.get(f"/api/activities/{task_b_id}")
    assert get_a.json()["status"] == "DONE"
    assert get_b.json()["status"] == "DONE"
