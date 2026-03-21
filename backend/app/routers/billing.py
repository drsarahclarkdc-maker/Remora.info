from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
import os
import logging
import asyncio
import stripe

from app.database import db
from app.models import User, PLANS, RECHARGE_PACKS
from app.auth import get_current_user, get_user_credits

logger = logging.getLogger(__name__)
router = APIRouter()

stripe.api_key = os.environ.get("STRIPE_API_KEY")

# In-memory cache of plan_id -> stripe_price_id
_stripe_prices = {}

PAID_PLAN_IDS = [p for p in PLANS if PLANS[p]["price"] > 0 and p != "enterprise"]


# ---------- Request Models ----------

class SubscribeRequest(BaseModel):
    plan_id: str
    origin_url: str


class ChangePlanRequest(BaseModel):
    plan_id: str


# ---------- Stripe Helpers ----------

async def get_or_create_stripe_price(plan_id: str) -> str:
    if plan_id in _stripe_prices:
        return _stripe_prices[plan_id]

    price_doc = await db.stripe_prices.find_one({"plan_id": plan_id}, {"_id": 0})
    if price_doc:
        _stripe_prices[plan_id] = price_doc["stripe_price_id"]
        return price_doc["stripe_price_id"]

    plan = PLANS[plan_id]
    product = await asyncio.to_thread(
        stripe.Product.create,
        name=f"Remora {plan['name']}",
        description=plan["description"],
    )
    price = await asyncio.to_thread(
        stripe.Price.create,
        product=product.id,
        unit_amount=int(plan["price"] * 100),
        currency="usd",
        recurring={"interval": "month"},
    )

    await db.stripe_prices.insert_one({
        "plan_id": plan_id,
        "stripe_product_id": product.id,
        "stripe_price_id": price.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    _stripe_prices[plan_id] = price.id
    return price.id


async def get_or_create_stripe_customer(user_id: str, email: str) -> str:
    billing = await db.user_billing.find_one({"user_id": user_id}, {"_id": 0})
    if billing and billing.get("stripe_customer_id"):
        return billing["stripe_customer_id"]

    customer = await asyncio.to_thread(
        stripe.Customer.create,
        email=email,
        metadata={"user_id": user_id},
    )

    await db.user_billing.update_one(
        {"user_id": user_id},
        {"$set": {"stripe_customer_id": customer.id}},
        upsert=True,
    )
    return customer.id


def _plan_rank(plan_id: str) -> int:
    order = ["free", "starter", "growth", "scale", "enterprise"]
    return order.index(plan_id) if plan_id in order else -1


# ---------- Public Endpoints ----------

@router.get("/billing/plans")
async def list_plans():
    return [{"plan_id": k, **v} for k, v in PLANS.items()]


# ---------- Usage ----------

@router.get("/billing/usage")
async def get_billing_usage(user: User = Depends(get_current_user)):
    billing = await get_user_credits(user.user_id)
    plan_info = PLANS.get(billing.get("plan", "free"), PLANS["free"])

    recent = await db.credit_usage.find(
        {"user_id": user.user_id}, {"_id": 0}
    ).sort("timestamp", -1).limit(20).to_list(20)

    total_credits = plan_info["credits"]
    used = billing.get("credits_used", 0)
    remaining = billing.get("credits_remaining", total_credits)
    usage_pct = round((used / total_credits) * 100, 1) if total_credits > 0 else 0

    return {
        "plan": billing.get("plan", "free"),
        "plan_name": plan_info["name"],
        "plan_price": plan_info["price"],
        "credits_total": total_credits,
        "credits_used": used,
        "credits_remaining": remaining,
        "usage_percentage": usage_pct,
        "alert": usage_pct >= 80,
        "period_start": billing.get("period_start"),
        "period_end": billing.get("period_end"),
        "recent_usage": recent,
        "has_subscription": bool(billing.get("stripe_subscription_id")),
        "subscription_status": billing.get("subscription_status"),
    }


# ---------- Subscribe (new subscription via Checkout) ----------

@router.post("/billing/checkout")
async def create_subscription_checkout(req: SubscribeRequest, request: Request, user: User = Depends(get_current_user)):
    plan_id = req.plan_id
    if plan_id not in PAID_PLAN_IDS:
        raise HTTPException(status_code=400, detail="Invalid plan. Choose starter, growth, or scale.")

    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    email = user_doc.get("email", "")

    customer_id = await get_or_create_stripe_customer(user.user_id, email)
    price_id = await get_or_create_stripe_price(plan_id)

    origin_url = req.origin_url.rstrip("/")
    success_url = f"{origin_url}/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/billing"

    session = await asyncio.to_thread(
        stripe.checkout.Session.create,
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user.user_id, "plan_id": plan_id},
        subscription_data={"metadata": {"user_id": user.user_id, "plan_id": plan_id}},
    )

    await db.payment_transactions.insert_one({
        "session_id": session.id,
        "user_id": user.user_id,
        "plan_id": plan_id,
        "amount": PLANS[plan_id]["price"],
        "currency": "usd",
        "credits": PLANS[plan_id]["credits"],
        "payment_status": "pending",
        "status": "initiated",
        "type": "subscription",
        "metadata": {"user_id": user.user_id, "plan_id": plan_id},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"url": session.url, "session_id": session.id}


# ---------- Poll Checkout Status ----------

@router.get("/billing/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, user: User = Depends(get_current_user)):
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    try:
        session = await asyncio.to_thread(
            stripe.checkout.Session.retrieve, session_id
        )
    except Exception as e:
        logger.warning(f"Stripe session retrieve error: {e}")
        return {
            "status": txn.get("status", "pending"),
            "payment_status": txn.get("payment_status", "pending"),
        }

    if txn.get("payment_status") != "paid" and session.payment_status == "paid":
        plan_id = txn.get("plan_id", "free")
        credits = txn.get("credits", PLANS.get(plan_id, PLANS["free"])["credits"])
        now = datetime.now(timezone.utc)

        update_fields = {
            "plan": plan_id,
            "credits_remaining": credits,
            "credits_used": 0,
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
            "subscription_status": "active",
        }

        # Store subscription details if subscription mode
        sub_id = getattr(session, "subscription", None)
        if sub_id:
            sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
            update_fields["stripe_subscription_id"] = sub.id
            if sub.items and sub.items.data:
                update_fields["stripe_subscription_item_id"] = sub.items.data[0].id
                update_fields["stripe_current_price_id"] = sub.items.data[0].price.id

        await db.user_billing.update_one(
            {"user_id": user.user_id},
            {"$set": update_fields},
            upsert=True,
        )
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": "paid",
                "status": "completed",
                "stripe_subscription_id": sub_id,
                "completed_at": now.isoformat(),
            }},
        )
    elif session.status == "expired":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "expired", "status": "expired"}},
        )

    return {
        "status": session.status,
        "payment_status": session.payment_status,
        "amount_total": getattr(session, "amount_total", 0),
        "currency": getattr(session, "currency", "usd"),
    }


# ---------- Change Plan (upgrade / downgrade with proration) ----------

@router.post("/billing/change-plan")
async def change_plan(req: ChangePlanRequest, user: User = Depends(get_current_user)):
    new_plan_id = req.plan_id
    if new_plan_id not in PAID_PLAN_IDS:
        raise HTTPException(status_code=400, detail="Invalid plan. Choose starter, growth, or scale.")

    billing = await db.user_billing.find_one({"user_id": user.user_id}, {"_id": 0})
    if not billing or not billing.get("stripe_subscription_id"):
        raise HTTPException(status_code=400, detail="No active subscription. Use /billing/checkout to subscribe first.")

    current_plan = billing.get("plan", "free")
    if current_plan == new_plan_id:
        raise HTTPException(status_code=400, detail="Already on this plan.")

    sub_id = billing["stripe_subscription_id"]
    item_id = billing.get("stripe_subscription_item_id")
    if not item_id:
        sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
        item_id = sub.items.data[0].id

    new_price_id = await get_or_create_stripe_price(new_plan_id)

    updated_sub = await asyncio.to_thread(
        stripe.Subscription.modify,
        sub_id,
        items=[{"id": item_id, "price": new_price_id}],
        proration_behavior="always_invoice",
    )

    new_item = updated_sub.items.data[0]
    new_credits = PLANS[new_plan_id]["credits"]
    now = datetime.now(timezone.utc)

    await db.user_billing.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "plan": new_plan_id,
            "credits_remaining": new_credits,
            "credits_used": 0,
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
            "stripe_subscription_item_id": new_item.id,
            "stripe_current_price_id": new_item.price.id,
            "subscription_status": updated_sub.status,
        }},
    )

    await db.payment_transactions.insert_one({
        "user_id": user.user_id,
        "plan_id": new_plan_id,
        "previous_plan": current_plan,
        "amount": PLANS[new_plan_id]["price"],
        "currency": "usd",
        "credits": new_credits,
        "payment_status": "paid",
        "status": "completed",
        "type": "plan_change",
        "stripe_subscription_id": sub_id,
        "created_at": now.isoformat(),
    })

    direction = "upgraded" if _plan_rank(new_plan_id) > _plan_rank(current_plan) else "downgraded"
    return {
        "message": f"Plan {direction} to {PLANS[new_plan_id]['name']}. Proration applied.",
        "plan": new_plan_id,
        "credits_remaining": new_credits,
    }


# ---------- Cancel Subscription ----------

@router.post("/billing/cancel")
async def cancel_subscription(user: User = Depends(get_current_user)):
    billing = await db.user_billing.find_one({"user_id": user.user_id}, {"_id": 0})
    if not billing or not billing.get("stripe_subscription_id"):
        raise HTTPException(status_code=400, detail="No active subscription to cancel.")

    sub_id = billing["stripe_subscription_id"]

    await asyncio.to_thread(stripe.Subscription.cancel, sub_id)

    now = datetime.now(timezone.utc)
    free_credits = PLANS["free"]["credits"]
    await db.user_billing.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "plan": "free",
            "credits_remaining": free_credits,
            "credits_used": 0,
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
            "stripe_subscription_id": None,
            "stripe_subscription_item_id": None,
            "stripe_current_price_id": None,
            "subscription_status": "canceled",
        }},
    )

    await db.payment_transactions.insert_one({
        "user_id": user.user_id,
        "plan_id": "free",
        "amount": 0,
        "currency": "usd",
        "credits": free_credits,
        "payment_status": "n/a",
        "status": "completed",
        "type": "cancellation",
        "created_at": now.isoformat(),
    })

    return {"message": "Subscription cancelled. Reverted to Free plan (1,000 credits).", "plan": "free"}


# ---------- Subscription Info ----------

@router.get("/billing/subscription")
async def get_subscription_info(user: User = Depends(get_current_user)):
    billing = await db.user_billing.find_one({"user_id": user.user_id}, {"_id": 0})
    if not billing or not billing.get("stripe_subscription_id"):
        return {"has_subscription": False, "plan": billing.get("plan", "free") if billing else "free"}

    try:
        sub = await asyncio.to_thread(
            stripe.Subscription.retrieve, billing["stripe_subscription_id"]
        )
        return {
            "has_subscription": True,
            "plan": billing.get("plan", "free"),
            "subscription_status": sub.status,
            "current_period_start": datetime.fromtimestamp(sub.current_period_start, tz=timezone.utc).isoformat(),
            "current_period_end": datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc).isoformat(),
            "cancel_at_period_end": sub.cancel_at_period_end,
        }
    except Exception as e:
        logger.warning(f"Error fetching subscription: {e}")
        return {
            "has_subscription": bool(billing.get("stripe_subscription_id")),
            "plan": billing.get("plan", "free"),
            "subscription_status": billing.get("subscription_status"),
        }


# ---------- Transactions ----------

@router.get("/billing/transactions")
async def list_transactions(user: User = Depends(get_current_user)):
    txns = await db.payment_transactions.find(
        {"user_id": user.user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    return txns


# ---------- Stripe Webhook ----------

@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get("Stripe-Signature", "")

    # Try to construct event with webhook secret if available
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    if webhook_secret and sig:
        try:
            event = stripe.Webhook.construct_event(body, sig, webhook_secret)
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Fallback: parse raw JSON (no signature verification)
        import json
        try:
            event = json.loads(body)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type") if isinstance(event, dict) else event.type
    data_obj = event.get("data", {}).get("object", {}) if isinstance(event, dict) else event.data.object

    try:
        if event_type == "checkout.session.completed":
            await _handle_checkout_completed(data_obj)
        elif event_type == "invoice.paid":
            await _handle_invoice_paid(data_obj)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(data_obj)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(data_obj)
    except Exception as e:
        logger.error(f"Webhook handler error for {event_type}: {e}")

    return {"status": "ok"}


async def _handle_checkout_completed(session):
    session_id = session.get("id") if isinstance(session, dict) else session.id
    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn or txn.get("payment_status") == "paid":
        return

    payment_status = session.get("payment_status") if isinstance(session, dict) else getattr(session, "payment_status", None)
    if payment_status != "paid":
        return

    user_id = txn.get("user_id")
    plan_id = txn.get("plan_id", "free")
    credits = txn.get("credits", PLANS.get(plan_id, PLANS["free"])["credits"])
    now = datetime.now(timezone.utc)

    sub_id = session.get("subscription") if isinstance(session, dict) else getattr(session, "subscription", None)

    update_fields = {
        "plan": plan_id,
        "credits_remaining": credits,
        "credits_used": 0,
        "period_start": now.isoformat(),
        "period_end": (now + timedelta(days=30)).isoformat(),
        "subscription_status": "active",
    }

    if sub_id:
        update_fields["stripe_subscription_id"] = sub_id
        try:
            sub = await asyncio.to_thread(stripe.Subscription.retrieve, sub_id)
            if sub.items and sub.items.data:
                update_fields["stripe_subscription_item_id"] = sub.items.data[0].id
                update_fields["stripe_current_price_id"] = sub.items.data[0].price.id
        except Exception:
            pass

    await db.user_billing.update_one(
        {"user_id": user_id},
        {"$set": update_fields},
        upsert=True,
    )
    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {"$set": {"payment_status": "paid", "status": "completed", "completed_at": now.isoformat()}},
    )


async def _handle_invoice_paid(invoice):
    sub_id = invoice.get("subscription") if isinstance(invoice, dict) else getattr(invoice, "subscription", None)
    if not sub_id:
        return

    billing = await db.user_billing.find_one({"stripe_subscription_id": sub_id}, {"_id": 0})
    if not billing:
        return

    plan_id = billing.get("plan", "free")
    credits = PLANS.get(plan_id, PLANS["free"])["credits"]
    now = datetime.now(timezone.utc)

    await db.user_billing.update_one(
        {"user_id": billing["user_id"]},
        {"$set": {
            "credits_remaining": credits,
            "credits_used": 0,
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
            "subscription_status": "active",
        }},
    )
    logger.info(f"Monthly renewal: reset {credits} credits for user {billing['user_id']}")


async def _handle_subscription_updated(sub_obj):
    sub_id = sub_obj.get("id") if isinstance(sub_obj, dict) else sub_obj.id
    billing = await db.user_billing.find_one({"stripe_subscription_id": sub_id}, {"_id": 0})
    if not billing:
        return
    status = sub_obj.get("status") if isinstance(sub_obj, dict) else getattr(sub_obj, "status", None)
    await db.user_billing.update_one(
        {"user_id": billing["user_id"]},
        {"$set": {"subscription_status": status}},
    )


async def _handle_subscription_deleted(sub_obj):
    sub_id = sub_obj.get("id") if isinstance(sub_obj, dict) else sub_obj.id
    billing = await db.user_billing.find_one({"stripe_subscription_id": sub_id}, {"_id": 0})
    if not billing:
        return

    now = datetime.now(timezone.utc)
    free_credits = PLANS["free"]["credits"]
    await db.user_billing.update_one(
        {"user_id": billing["user_id"]},
        {"$set": {
            "plan": "free",
            "credits_remaining": free_credits,
            "credits_used": 0,
            "period_start": now.isoformat(),
            "period_end": (now + timedelta(days=30)).isoformat(),
            "stripe_subscription_id": None,
            "stripe_subscription_item_id": None,
            "stripe_current_price_id": None,
            "subscription_status": "canceled",
        }},
    )
    logger.info(f"Subscription {sub_id} deleted → user {billing['user_id']} reverted to Free")


# ---------- Recharge Packs ----------

@router.get("/billing/recharge-packs")
async def list_recharge_packs():
    return [{"pack_id": k, **v} for k, v in RECHARGE_PACKS.items()]


# ---------- Auto-Recharge Settings ----------

class AutoRechargeSettings(BaseModel):
    enabled: bool
    pack_id: str = "medium"


@router.get("/billing/settings")
async def get_billing_settings(user: User = Depends(get_current_user)):
    billing = await db.user_billing.find_one({"user_id": user.user_id}, {"_id": 0})
    return {
        "auto_recharge_enabled": billing.get("auto_recharge_enabled", False) if billing else False,
        "recharge_pack_id": billing.get("recharge_pack_id", "medium") if billing else "medium",
        "has_payment_method": bool(billing.get("stripe_customer_id")) if billing else False,
    }


@router.put("/billing/settings")
async def update_billing_settings(settings: AutoRechargeSettings, user: User = Depends(get_current_user)):
    if settings.pack_id not in RECHARGE_PACKS:
        raise HTTPException(status_code=400, detail="Invalid recharge pack. Choose small, medium, or large.")

    billing = await db.user_billing.find_one({"user_id": user.user_id}, {"_id": 0})
    if settings.enabled and (not billing or not billing.get("stripe_customer_id")):
        raise HTTPException(
            status_code=400,
            detail="A payment method is required. Subscribe to a plan first to enable auto-recharge."
        )

    await db.user_billing.update_one(
        {"user_id": user.user_id},
        {"$set": {
            "auto_recharge_enabled": settings.enabled,
            "recharge_pack_id": settings.pack_id,
        }},
        upsert=True,
    )

    return {
        "message": f"Auto-recharge {'enabled' if settings.enabled else 'disabled'}.",
        "auto_recharge_enabled": settings.enabled,
        "recharge_pack_id": settings.pack_id,
    }
