"""Staff domain models: users, profiles, roles, and auth tokens."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class StaffRole(StrEnum):
    REGIONAL_MANAGER = "REGIONAL_MANAGER"
    STORE_MANAGER = "STORE_MANAGER"
    DEPARTMENT_LEAD = "DEPARTMENT_LEAD"
    ASSOCIATE = "ASSOCIATE"


class UserProfile(BaseModel):
    """Optional profile detail, kept separate from the identity record."""

    phone: str | None = None
    bio: str | None = None


class User(BaseModel):
    id: str
    store_id: str
    name: str
    email: str
    staff_role: StaffRole
    profile: UserProfile = UserProfile()


class AuthToken(BaseModel):
    token: str
    user_id: str
