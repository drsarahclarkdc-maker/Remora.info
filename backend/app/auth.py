from fastapi import HTTPException, Request
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import hashlib
import uuid

from app.database import db
from app.models import User, UsageRecord, PLANS, CREDIT_COSTS
import logging

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> User:
    """Get current user from session token (cookie or header)"""
    session_token = request.cookies.get("session_token")

    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )

    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")

    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )

    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")

    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])

    return User(**user_doc)


async def get_user_from_api_key(request: Request) -> Optional[User]:
    """Get user from API key in X-API-Key header"""
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return None

    key_hash = hashlib.sha256(api_key.encode()).hexdigest()

    key_doc = await db.api_keys.find_one(
        {"key_hash": key_hash, "is_active": True},
        {"_id": 0}
    )

    if not key_doc:
        return None

    await db.api_keys.update_one(
        {"key_hash": key_hash},
        {"$set": {"last_used": datetime.now(timezone.utc).isoformat()}}
    )

    user_doc = await db.users.find_one(
        {"user_id": key_doc["user_id"]},
        {"_id": 0}
    )

    if not user_doc:
        return None

    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])

    return User(**user_doc)


async def record_usage(key_id: str, user_id: str, endpoint: str, method: str, status_code: int, response_time_ms: int):
    """Record API usage"""
    record = UsageRecord(
        record_id=f"usage_{uuid.uuid4().hex[:12]}",
        key_id=key_id,
        user_id=user_id,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=response_time_ms
    )
    doc = record.model_dump()
    doc["timestamp"] = doc["timestamp"].isoformat()
    await db.usage_records.insert_one(doc)


async def get_user_credits(user_id: str) -> Dict[str, Any]:
    """Get user's current credit balance and plan info"""
    billing = await db.user_billing.find_one({"user_id": user_id}, {"_id": 0})
    if not billing:
        now = datetime.now(timezone.utc)
        billing = {
            "user_id": user_id,
            "plan": "free",
            "credits_remaining": PLANS["free"]["credits"],
            "credits_used": 0,
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
        }
        await db.user_billing.insert_one(billing)
    return billing


async def deduct_credits(user_id: str, amount: int, operation: str) -> bool:
    """Deduct credits. Returns True if successful, False if insufficient."""
    billing = await get_user_credits(user_id)

    period_end = billing.get("period_end", "")
    if period_end:
        end_dt = datetime.fromisoformat(period_end) if isinstance(period_end, str) else period_end
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > end_dt:
            plan = billing.get("plan", "free")
            now = datetime.now(timezone.utc)
            await db.user_billing.update_one(
                {"user_id": user_id},
                {"$set": {
                    "credits_remaining": PLANS.get(plan, PLANS["free"])["credits"],
                    "credits_used": 0,
                    "period_start": now.isoformat(),
                    "period_end": (now + timedelta(days=30)).isoformat(),
                }}
            )
            billing = await get_user_credits(user_id)

    if billing["credits_remaining"] < amount:
        return False

    await db.user_billing.update_one(
        {"user_id": user_id},
        {"$inc": {"credits_remaining": -amount, "credits_used": amount}}
    )

    await db.credit_usage.insert_one({
        "user_id": user_id,
        "operation": operation,
        "credits": amount,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

    return True


async def check_credits_or_block(user_id: str, amount: int, operation: str):
    """Check credits and raise 402 if insufficient"""
    success = await deduct_credits(user_id, amount, operation)
    if not success:
        raise HTTPException(
            status_code=402,
            detail="Credit limit reached. Upgrade your plan at /billing."
        )
