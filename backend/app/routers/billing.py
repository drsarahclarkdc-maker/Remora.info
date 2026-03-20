from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone, timedelta
import os
import logging

from app.database import db
from app.models import User, CheckoutRequest, PLANS, CREDIT_COSTS
from app.auth import get_current_user, get_user_credits

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/billing/plans")
async def list_plans():
    return [{"plan_id": k, **v} for k, v in PLANS.items()]


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
    }


@router.post("/billing/checkout")
async def create_checkout(checkout_req: CheckoutRequest, request: Request, user: User = Depends(get_current_user)):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout, CheckoutSessionRequest

    plan_id = checkout_req.plan_id
    if plan_id not in PLANS or plan_id == "free" or plan_id == "enterprise":
        raise HTTPException(status_code=400, detail="Invalid plan. Choose starter, growth, or scale.")

    plan = PLANS[plan_id]
    api_key = os.environ.get("STRIPE_API_KEY")

    origin_url = checkout_req.origin_url.rstrip("/")
    success_url = f"{origin_url}/billing?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{origin_url}/billing"

    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"

    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)

    checkout_request = CheckoutSessionRequest(
        amount=plan["price"],
        currency="usd",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            "user_id": user.user_id,
            "plan_id": plan_id,
            "plan_name": plan["name"],
            "credits": str(plan["credits"]),
        }
    )

    session = await stripe_checkout.create_checkout_session(checkout_request)

    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user.user_id,
        "plan_id": plan_id,
        "amount": plan["price"],
        "currency": "usd",
        "credits": plan["credits"],
        "payment_status": "pending",
        "status": "initiated",
        "metadata": {"user_id": user.user_id, "plan_id": plan_id},
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    return {"url": session.url, "session_id": session.session_id}


@router.get("/billing/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request, user: User = Depends(get_current_user)):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    api_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"

    try:
        stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
        checkout_status = await stripe_checkout.get_checkout_status(session_id)
    except Exception as e:
        logger.warning(f"Stripe status check error: {e}")
        return {
            "status": txn.get("status", "pending"),
            "payment_status": txn.get("payment_status", "pending"),
            "amount_total": txn.get("amount", 0),
            "currency": txn.get("currency", "usd"),
        }

    if txn.get("payment_status") != "paid" and checkout_status.payment_status == "paid":
        plan_id = txn.get("plan_id", "free")
        credits = txn.get("credits", PLANS.get(plan_id, PLANS["free"])["credits"])
        now = datetime.now(timezone.utc)
        await db.user_billing.update_one(
            {"user_id": user.user_id},
            {"$set": {
                "plan": plan_id,
                "credits_remaining": credits,
                "credits_used": 0,
                "period_start": now.isoformat(),
                "period_end": (now + timedelta(days=30)).isoformat(),
            }},
            upsert=True
        )
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "paid", "status": "completed", "completed_at": now.isoformat()}}
        )
    elif checkout_status.status == "expired":
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {"payment_status": "expired", "status": "expired"}}
        )

    return {
        "status": checkout_status.status,
        "payment_status": checkout_status.payment_status,
        "amount_total": checkout_status.amount_total,
        "currency": checkout_status.currency,
    }


@router.get("/billing/transactions")
async def list_transactions(user: User = Depends(get_current_user)):
    txns = await db.payment_transactions.find(
        {"user_id": user.user_id}, {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    return txns


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    api_key = os.environ.get("STRIPE_API_KEY")
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"

    stripe_checkout = StripeCheckout(api_key=api_key, webhook_url=webhook_url)
    body = await request.body()
    signature = request.headers.get("Stripe-Signature", "")

    try:
        webhook_response = await stripe_checkout.handle_webhook(body, signature)

        if webhook_response.payment_status == "paid":
            session_id = webhook_response.session_id
            txn = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})

            if txn and txn.get("payment_status") != "paid":
                user_id = txn.get("user_id") or webhook_response.metadata.get("user_id")
                plan_id = txn.get("plan_id") or webhook_response.metadata.get("plan_id", "free")
                credits = txn.get("credits", PLANS.get(plan_id, PLANS["free"])["credits"])
                now = datetime.now(timezone.utc)

                await db.user_billing.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "plan": plan_id,
                        "credits_remaining": credits,
                        "credits_used": 0,
                        "period_start": now.isoformat(),
                        "period_end": (now + timedelta(days=30)).isoformat(),
                    }},
                    upsert=True
                )
                await db.payment_transactions.update_one(
                    {"session_id": session_id},
                    {"$set": {"payment_status": "paid", "status": "completed", "completed_at": now.isoformat()}}
                )

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return {"status": "error", "message": str(e)}
