from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import uuid
import secrets

from app.database import db
from app.models import User, Webhook, WebhookCreate, WebhookUpdate
from app.auth import get_current_user

router = APIRouter()


@router.get("/webhooks")
async def list_webhooks(user: User = Depends(get_current_user)):
    webhooks = await db.webhooks.find({"user_id": user.user_id}, {"_id": 0, "secret": 0}).to_list(100)
    for webhook in webhooks:
        webhook["secret"] = "***"
        if isinstance(webhook.get("created_at"), str):
            webhook["created_at"] = datetime.fromisoformat(webhook["created_at"])
        if isinstance(webhook.get("last_delivery"), str):
            webhook["last_delivery"] = datetime.fromisoformat(webhook["last_delivery"])
    return webhooks


@router.post("/webhooks")
async def create_webhook(webhook_data: WebhookCreate, user: User = Depends(get_current_user)):
    webhook = Webhook(
        webhook_id=f"wh_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        name=webhook_data.name,
        url=webhook_data.url,
        events=webhook_data.events,
        secret=secrets.token_urlsafe(24)
    )
    doc = webhook.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.webhooks.insert_one(doc)
    return webhook.model_dump()


@router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, webhook_data: WebhookUpdate, user: User = Depends(get_current_user)):
    update_data = {k: v for k, v in webhook_data.model_dump().items() if v is not None}
    result = await db.webhooks.update_one(
        {"webhook_id": webhook_id, "user_id": user.user_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    webhook_doc = await db.webhooks.find_one({"webhook_id": webhook_id}, {"_id": 0, "secret": 0})
    webhook_doc["secret"] = "***"
    if isinstance(webhook_doc.get("created_at"), str):
        webhook_doc["created_at"] = datetime.fromisoformat(webhook_doc["created_at"])
    return webhook_doc


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, user: User = Depends(get_current_user)):
    result = await db.webhooks.delete_one({"webhook_id": webhook_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return {"message": "Webhook deleted"}


# Delivery logs
@router.get("/webhooks/deliveries")
async def list_webhook_deliveries(user: User = Depends(get_current_user), limit: int = 50):
    logs = await db.webhook_delivery_logs.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return logs


@router.get("/webhooks/{webhook_id}/deliveries")
async def list_webhook_deliveries_by_id(webhook_id: str, user: User = Depends(get_current_user), limit: int = 50):
    webhook = await db.webhooks.find_one({"webhook_id": webhook_id, "user_id": user.user_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    logs = await db.webhook_delivery_logs.find({"webhook_id": webhook_id}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return logs


@router.get("/webhooks/deliveries/stats")
async def get_webhook_delivery_stats(user: User = Depends(get_current_user)):
    total = await db.webhook_delivery_logs.count_documents({"user_id": user.user_id})
    success = await db.webhook_delivery_logs.count_documents({"user_id": user.user_id, "status": "success"})
    failed = await db.webhook_delivery_logs.count_documents({"user_id": user.user_id, "status": "failed"})
    pending = await db.webhook_delivery_logs.count_documents({"user_id": user.user_id, "status": {"$in": ["pending", "retrying"]}})
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "pending": pending,
        "success_rate": round((success / total * 100) if total > 0 else 0, 2)
    }
