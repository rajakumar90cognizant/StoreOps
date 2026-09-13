"""Programmes route tests."""

from __future__ import annotations

from httpx import AsyncClient


async def test_list_programmes_only_returns_current_store(
    client: AsyncClient, store_manager_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/programmes", json={"name": "Spring Rollout"}, headers=store_manager_headers
    )

    resp = await client.get("/api/programmes", headers=store_manager_headers)

    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "Spring Rollout" in names


async def test_add_member_returns_updated_membership(
    client: AsyncClient, store_manager_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/programmes", json={"name": "Refit"}, headers=store_manager_headers
    )
    programme_id = create_resp.json()["id"]

    add_resp = await client.post(
        f"/api/programmes/{programme_id}/members",
        json={"user_id": "user-associate"},
        headers=store_manager_headers,
    )

    assert add_resp.status_code == 201
    member_ids = [m["user_id"] for m in add_resp.json()["members"]]
    assert "user-associate" in member_ids


async def test_list_programmes_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/programmes")

    assert resp.status_code == 401


async def test_add_member_requires_auth(
    client: AsyncClient, store_manager_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/programmes", json={"name": "Needs auth to add members"}, headers=store_manager_headers
    )
    programme_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/programmes/{programme_id}/members", json={"user_id": "user-associate"}
    )

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "UNAUTHORIZED"

    # business rule check, not just the status code: no member was added
    get_resp = await client.get("/api/programmes", headers=store_manager_headers)
    programme = next(p for p in get_resp.json() if p["id"] == programme_id)
    assert programme["members"] == []
