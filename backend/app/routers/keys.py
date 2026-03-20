from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
import uuid
import secrets
import hashlib

from app.database import db
from app.models import User, APIKey, APIKeyCreate, APIKeyResponse, APIKeyCreatedResponse
from app.auth import get_current_user

router = APIRouter()


@router.get("/keys", response_model=List[APIKeyResponse])
async def list_api_keys(user: User = Depends(get_current_user)):
    """List all API keys for current user"""
    keys = await db.api_keys.find(
        {"user_id": user.user_id},
        {"_id": 0, "key_hash": 0}
    ).to_list(100)

    for key in keys:
        if isinstance(key.get("created_at"), str):
            key["created_at"] = datetime.fromisoformat(key["created_at"])
        if isinstance(key.get("last_used"), str):
            key["last_used"] = datetime.fromisoformat(key["last_used"])

    return keys


@router.post("/keys", response_model=APIKeyCreatedResponse)
async def create_api_key(key_data: APIKeyCreate, user: User = Depends(get_current_user)):
    """Create a new API key"""
    api_key = f"rmr_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    prefix = api_key[:12]

    key = APIKey(
        key_id=f"key_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        name=key_data.name,
        key_hash=key_hash,
        prefix=prefix
    )

    doc = key.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.api_keys.insert_one(doc)

    return APIKeyCreatedResponse(
        key_id=key.key_id,
        name=key.name,
        api_key=api_key,
        prefix=prefix,
        created_at=key.created_at
    )


@router.delete("/keys/{key_id}")
async def revoke_api_key(key_id: str, user: User = Depends(get_current_user)):
    """Revoke an API key"""
    result = await db.api_keys.delete_one({
        "key_id": key_id,
        "user_id": user.user_id
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"message": "API key revoked"}
