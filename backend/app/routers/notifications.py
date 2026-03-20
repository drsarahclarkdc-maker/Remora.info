from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from app.database import db
from app.models import User
from app.auth import get_current_user

router = APIRouter()


@router.get("/notifications")
async def list_notifications(user: User = Depends(get_current_user), unread_only: bool = False):
    query = {"user_id": user.user_id}
    if unread_only:
        query["read"] = False
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).limit(30).to_list(30)
    unread_count = await db.notifications.count_documents({"user_id": user.user_id, "read": False})
    return {"notifications": notifications, "unread_count": unread_count}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user: User = Depends(get_current_user)):
    result = await db.notifications.update_one(
        {"notification_id": notification_id, "user_id": user.user_id},
        {"$set": {"read": True}}
    )
    if result.modified_count == 0:
        return {"message": "Notification not found or already read"}
    return {"message": "Marked as read"}


@router.post("/notifications/read-all")
async def mark_all_read(user: User = Depends(get_current_user)):
    result = await db.notifications.update_many(
        {"user_id": user.user_id, "read": False},
        {"$set": {"read": True}}
    )
    return {"message": f"Marked {result.modified_count} notifications as read"}
