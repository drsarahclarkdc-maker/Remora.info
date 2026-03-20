from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta

from app.database import db
from app.models import User
from app.auth import get_current_user

router = APIRouter()


@router.get("/usage/stats")
async def get_usage_stats(user: User = Depends(get_current_user)):
    total_requests = await db.usage_records.count_documents({"user_id": user.user_id})
    total_keys = await db.api_keys.count_documents({"user_id": user.user_id})
    total_agents = await db.agents.count_documents({"user_id": user.user_id})
    total_webhooks = await db.webhooks.count_documents({"user_id": user.user_id})
    total_content = await db.crawled_content.count_documents({})
    now = datetime.now(timezone.utc)
    day_ago = (now - timedelta(days=1)).isoformat()
    requests_24h = await db.usage_records.count_documents({
        "user_id": user.user_id,
        "timestamp": {"$gte": day_ago}
    })
    return {
        "total_requests": total_requests,
        "requests_24h": requests_24h,
        "total_api_keys": total_keys,
        "total_agents": total_agents,
        "total_webhooks": total_webhooks,
        "total_content": total_content,
        "plan": "free"
    }


@router.get("/usage/recent")
async def get_recent_usage(user: User = Depends(get_current_user), limit: int = 20):
    records = await db.usage_records.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    return records
