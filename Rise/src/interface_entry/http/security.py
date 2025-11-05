from __future__ import annotations

"""HTTP security and actor context dependencies."""

from dataclasses import dataclass
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, Request, status

from project_utility.context import ContextBridge


@dataclass(slots=True)
class ActorContext:
    actor_id: str
    roles: Tuple[str, ...]
    tenant_id: Optional[str]
    request_id: str


def get_actor_context(request: Request) -> ActorContext:
    actor_id = (
        request.headers.get("X-Actor-Id")
        or request.headers.get("X-User-Id")
        or request.headers.get("X-Request-Actor")
    )
    if not actor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHENTICATED", "message": "Missing actor headers"},
        )
    roles_header = request.headers.get("X-Actor-Roles", "")
    roles = tuple(role.strip() for role in roles_header.split(",") if role.strip())
    tenant = request.headers.get("X-Tenant-Id") or request.headers.get("X-Org-Id")
    return ActorContext(
        actor_id=actor_id,
        roles=roles,
        tenant_id=tenant,
        request_id=ContextBridge.request_id(),
    )


ActorContextDependency = Depends(get_actor_context)

