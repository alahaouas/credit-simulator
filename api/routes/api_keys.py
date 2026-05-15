"""GET/POST/DELETE /api/keys — API key management (E3)."""
from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import hash_api_key, require_user
from ..constants import API_KEY_DISPLAY_PREFIX_LEN, API_KEY_PREFIX
from ..db import get_db

router = APIRouter()


def _generate_key() -> tuple[str, str, str]:
    """Return (full_key, pbkdf2_hash, display_prefix)."""
    raw = secrets.token_hex(32)
    full_key = f"{API_KEY_PREFIX}{raw}"
    key_hash = hash_api_key(full_key)
    key_prefix = full_key[:API_KEY_DISPLAY_PREFIX_LEN]
    return full_key, key_hash, key_prefix


class CreateKeyRequest(BaseModel):
    name: str


@router.get("/keys", summary="List API keys")
def list_keys(
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> list[dict]:
    resp = (
        db.table("api_keys")
        .select("id,name,key_prefix,created_at,last_used_at")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return resp.data or []


@router.post("/keys", status_code=201, summary="Create an API key")
def create_key(
    body: CreateKeyRequest,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> dict:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Key name cannot be empty")
    full_key, key_hash, key_prefix = _generate_key()
    payload = {
        "user_id": user_id,
        "name": name,
        "key_hash": key_hash,
        "key_prefix": key_prefix,
    }
    resp = db.table("api_keys").insert(payload).execute()
    row = resp.data[0] if resp.data else payload
    return {
        "id": row.get("id", ""),
        "name": row["name"],
        "key_prefix": row["key_prefix"],
        "created_at": row.get("created_at", ""),
        "key": full_key,
    }


@router.delete("/keys/{key_id}", status_code=204, summary="Revoke an API key")
def delete_key(
    key_id: str,
    user_id: str = Depends(require_user),
    db=Depends(get_db),
) -> None:
    resp = (
        db.table("api_keys")
        .delete()
        .eq("id", key_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail="API key not found")
