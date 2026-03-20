from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta

from app.database import db
from app.models import User
from app.auth import get_current_user

router = APIRouter()


@router.get("/usage/stats")
async def get_usage_stats(user: User = Depends(get_current_user)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    today_count = await db.usage_records.count_documents({
        "user_id": user.user_id,
        "timestamp": {"$gte": today_start.isoformat()}
    })

    week_start = today_start - timedelta(days=today_start.weekday())
    week_count = await db.usage_records.count_documents({
        "user_id": user.user_id,
        "timestamp": {"$gte": week_start.isoformat()}
    })

    month_start = today_start.replace(day=1)
    month_count = await db.usage_records.count_documents({
        "user_id": user.user_id,
        "timestamp": {"$gte": month_start.isoformat()}
    })

    total_count = await db.usage_records.count_documents({"user_id": user.user_id})

    daily_stats = []
    for i in range(7):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = await db.usage_records.count_documents({
            "user_id": user.user_id,
            "timestamp": {
                "$gte": day_start.isoformat(),
                "$lt": day_end.isoformat()
            }
        })
        daily_stats.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "requests": count
        })

    pipeline = [
        {"$match": {"user_id": user.user_id}},
        {"$group": {"_id": None, "avg_response_time": {"$avg": "$response_time_ms"}}}
    ]
    avg_result = await db.usage_records.aggregate(pipeline).to_list(1)
    avg_response_time = avg_result[0]["avg_response_time"] if avg_result else 0

    return {
        "today": today_count,
        "this_week": week_count,
        "this_month": month_count,
        "total": total_count,
        "daily_breakdown": list(reversed(daily_stats)),
        "avg_response_time_ms": round(avg_response_time, 2),
        "plan": "free",
        "note": "Free for everyone! We're just tracking usage for now."
    }


@router.get("/usage/recent")
async def get_recent_usage(user: User = Depends(get_current_user), limit: int = 20):
    records = await db.usage_records.find(
        {"user_id": user.user_id}, {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    for record in records:
        if isinstance(record.get("timestamp"), str):
            record["timestamp"] = datetime.fromisoformat(record["timestamp"])
    return records
