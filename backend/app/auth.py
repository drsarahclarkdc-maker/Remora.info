from fastapi import HTTPException, Request
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import hashlib
import uuid
import asyncio
import os
import logging

from app.database import db
from app.models import User, UsageRecord, PLANS, CREDIT_COSTS, RECHARGE_PACKS

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

    # If plan credits were reduced (e.g. free 3000→1000), cap remaining to plan total
    plan = billing.get("plan", "free")
    plan_credits = PLANS.get(plan, PLANS["free"])["credits"]
    if plan_credits > 0 and billing.get("credits_remaining", 0) > plan_credits:
        billing["credits_remaining"] = plan_credits
        billing["credits_used"] = 0
        await db.user_billing.update_one(
            {"user_id": user_id},
            {"$set": {"credits_remaining": plan_credits, "credits_used": 0}}
        )

    return billing


async def _check_usage_alert(user_id: str, billing: dict):
    """Create a notification when usage hits 80%. One alert per billing period."""
    plan = billing.get("plan", "free")
    total = PLANS.get(plan, PLANS["free"])["credits"]
    used = billing.get("credits_used", 0)
    if total <= 0:
        return

    pct = (used / total) * 100
    if pct < 80:
        return

    period_start = billing.get("period_start", "")
    existing = await db.notifications.find_one({
        "user_id": user_id,
        "type": "usage_alert",
        "period_start": period_start,
    })
    if existing:
        return

    now = datetime.now(timezone.utc)
    await db.notifications.insert_one({
        "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "type": "usage_alert",
        "title": "Credit usage at 80%",
        "message": f"You've used {round(pct)}% of your {total:,} monthly credits. Consider upgrading your plan to avoid interruptions.",
        "read": False,
        "period_start": period_start,
        "created_at": now.isoformat(),
    })
    logger.info(f"80% usage alert created for user {user_id} ({round(pct)}% used)")


async def _try_auto_recharge(user_id: str, billing: dict) -> bool:
    """Attempt to auto-recharge credits via Stripe. Returns True if successful."""
    if not billing.get("auto_recharge_enabled"):
        return False

    customer_id = billing.get("stripe_customer_id")
    if not customer_id:
        return False

    pack_id = billing.get("recharge_pack_id", "medium")
    pack = RECHARGE_PACKS.get(pack_id)
    if not pack:
        return False

    import stripe
    stripe.api_key = os.environ.get("STRIPE_API_KEY")

    try:
        payment_intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            customer=customer_id,
            amount=int(pack["price"] * 100),
            currency="usd",
            confirm=True,
            off_session=True,
            description=f"Remora auto-recharge: {pack['credits']} credits",
        )

        if payment_intent.status == "succeeded":
            await db.user_billing.update_one(
                {"user_id": user_id},
                {"$inc": {"credits_remaining": pack["credits"]}}
            )
            now = datetime.now(timezone.utc)
            await db.payment_transactions.insert_one({
                "user_id": user_id,
                "plan_id": billing.get("plan", "free"),
                "amount": pack["price"],
                "currency": "usd",
                "credits": pack["credits"],
                "payment_status": "paid",
                "status": "completed",
                "type": "auto_recharge",
                "recharge_pack": pack_id,
                "stripe_payment_intent_id": payment_intent.id,
                "created_at": now.isoformat(),
            })
            await db.notifications.insert_one({
                "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
                "user_id": user_id,
                "type": "auto_recharge",
                "title": "Credits auto-recharged",
                "message": f"Added {pack['credits']:,} credits (${pack['price']}) via auto-recharge.",
                "read": False,
                "created_at": now.isoformat(),
            })
            logger.info(f"Auto-recharge success: {pack['credits']} credits for user {user_id}")
            return True

    except Exception as e:
        logger.error(f"Auto-recharge failed for user {user_id}: {e}")
        await db.notifications.insert_one({
            "notification_id": f"notif_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "type": "auto_recharge_failed",
            "title": "Auto-recharge failed",
            "message": f"Could not charge your payment method for {pack['credits']:,} credits. Please check your billing settings.",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    return False


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
        recharged = await _try_auto_recharge(user_id, billing)
        if recharged:
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

    # Check usage alert (non-blocking)
    billing["credits_used"] = billing.get("credits_used", 0) + amount
    asyncio.create_task(_check_usage_alert(user_id, billing))

    return True


async def check_credits_or_block(user_id: str, amount: int, operation: str):
    """Check credits and raise 402 if insufficient"""
    success = await deduct_credits(user_id, amount, operation)
    if not success:
        raise HTTPException(
            status_code=402,
            detail="Credit limit reached. Upgrade your plan at /billing."
        )
