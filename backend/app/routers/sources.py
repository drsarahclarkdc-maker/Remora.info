from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
import uuid
import hashlib
import logging

from app.database import db
from app.models import User, ContentSource, ContentSourceCreate, ContentSourceUpdate
from app.auth import get_current_user
from app.crawler import crawl_url

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/sources")
async def list_content_sources(user: User = Depends(get_current_user)):
    return await db.content_sources.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)


@router.post("/sources")
async def create_content_source(source_data: ContentSourceCreate, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    parsed = urlparse(source_data.url)
    domain = parsed.netloc
    existing = await db.content_sources.find_one({"user_id": user.user_id, "url": source_data.url})
    if existing:
        raise HTTPException(status_code=400, detail="Source URL already exists")
    source = ContentSource(
        source_id=f"src_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id, name=source_data.name, url=source_data.url,
        domain=domain, crawl_frequency=source_data.crawl_frequency
    )
    doc = source.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.content_sources.insert_one(doc)
    try:
        data = await crawl_url(source_data.url)
        content_id = f"content_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        content_doc = {
            "content_id": content_id, "url": data["url"], "title": data["title"],
            "description": data["description"], "content": data["content"],
            "structured_data": data["structured_data"], "domain": data["domain"],
            "source_id": source.source_id, "crawled_at": now.isoformat(), "last_updated": now.isoformat()
        }
        await db.crawled_content.update_one({"url": data["url"]}, {"$set": content_doc}, upsert=True)
        content_hash = hashlib.md5(data["content"].encode()).hexdigest()
        history_entry = {
            "history_id": f"hist_{uuid.uuid4().hex[:12]}",
            "content_id": content_id, "url": data["url"], "title": data["title"],
            "content_hash": content_hash, "word_count": len(data["content"].split()),
            "status": "success", "source": "source", "crawled_at": now.isoformat()
        }
        await db.crawl_history.insert_one(history_entry)
        await db.content_sources.update_one(
            {"source_id": source.source_id},
            {"$set": {"last_crawl": now.isoformat(), "last_status": "success", "content_count": 1}}
        )
    except Exception as e:
        await db.content_sources.update_one(
            {"source_id": source.source_id},
            {"$set": {"last_status": f"failed: {str(e)[:100]}"}}
        )
    if source_data.crawl_frequency:
        now = datetime.now(timezone.utc)
        if source_data.crawl_frequency == "hourly":
            next_crawl = now + timedelta(hours=1)
        elif source_data.crawl_frequency == "daily":
            next_crawl = now + timedelta(days=1)
        else:
            next_crawl = now + timedelta(weeks=1)
        schedule_doc = {
            "schedule_id": f"sched_{uuid.uuid4().hex[:12]}",
            "user_id": user.user_id, "url": source_data.url,
            "frequency": source_data.crawl_frequency, "is_active": True,
            "source_id": source.source_id, "next_crawl": next_crawl.isoformat(),
            "created_at": now.isoformat()
        }
        await db.scheduled_crawls.insert_one(schedule_doc)
    return source.model_dump()


@router.put("/sources/{source_id}")
async def update_content_source(source_id: str, source_data: ContentSourceUpdate, user: User = Depends(get_current_user)):
    update_data = {k: v for k, v in source_data.model_dump().items() if v is not None}
    result = await db.content_sources.update_one({"source_id": source_id, "user_id": user.user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Source not found")
    return await db.content_sources.find_one({"source_id": source_id}, {"_id": 0})


@router.delete("/sources/{source_id}")
async def delete_content_source(source_id: str, user: User = Depends(get_current_user)):
    result = await db.content_sources.delete_one({"source_id": source_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Source not found")
    await db.scheduled_crawls.delete_many({"source_id": source_id})
    return {"message": "Source deleted"}


@router.post("/sources/{source_id}/crawl")
async def crawl_content_source(source_id: str, user: User = Depends(get_current_user)):
    source = await db.content_sources.find_one({"source_id": source_id, "user_id": user.user_id})
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    try:
        data = await crawl_url(source["url"])
        content_id = f"content_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        existing = await db.crawled_content.find_one({"url": data["url"]}, {"_id": 0})
        if existing:
            content_id = existing["content_id"]
        content_doc = {
            "content_id": content_id, "url": data["url"], "title": data["title"],
            "description": data["description"], "content": data["content"],
            "structured_data": data["structured_data"], "domain": data["domain"],
            "source_id": source_id, "crawled_at": now.isoformat(), "last_updated": now.isoformat()
        }
        await db.crawled_content.update_one({"url": data["url"]}, {"$set": content_doc}, upsert=True)
        content_hash = hashlib.md5(data["content"].encode()).hexdigest()
        history_entry = {
            "history_id": f"hist_{uuid.uuid4().hex[:12]}",
            "content_id": content_id, "url": data["url"], "title": data["title"],
            "content_hash": content_hash, "word_count": len(data["content"].split()),
            "status": "success", "source": "manual", "crawled_at": now.isoformat()
        }
        await db.crawl_history.insert_one(history_entry)
        await db.content_sources.update_one(
            {"source_id": source_id},
            {"$set": {"last_crawl": now.isoformat(), "last_status": "success"},
             "$inc": {"content_count": 1 if not existing else 0}}
        )
        return {"status": "success", "content_id": content_id, "title": data["title"]}
    except Exception as e:
        await db.content_sources.update_one(
            {"source_id": source_id},
            {"$set": {"last_status": f"failed: {str(e)[:100]}"}}
        )
        raise HTTPException(status_code=400, detail=f"Crawl failed: {str(e)}")
