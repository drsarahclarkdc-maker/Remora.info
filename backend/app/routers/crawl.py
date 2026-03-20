from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
from typing import List
from datetime import datetime, timezone, timedelta
import uuid
import hashlib
import asyncio
import logging

from app.database import db
from app.models import (
    User, CrawledContent, CrawlRequest, BulkCrawlRequest, BulkCrawlResponse, CrawlJob,
    ScheduledCrawl, ScheduledCrawlCreate, CREDIT_COSTS,
)
from app.auth import get_current_user, get_user_from_api_key, check_credits_or_block
from app.crawler import crawl_url, queue_webhook_delivery

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/content")
async def list_content(user: User = Depends(get_current_user), limit: int = 50):
    content = await db.crawled_content.find({}, {"_id": 0}).sort("crawled_at", -1).limit(limit).to_list(limit)
    for item in content:
        if isinstance(item.get("crawled_at"), str):
            item["crawled_at"] = datetime.fromisoformat(item["crawled_at"])
        if isinstance(item.get("last_updated"), str):
            item["last_updated"] = datetime.fromisoformat(item["last_updated"])
    return content


@router.get("/content/{content_id}")
async def get_content(content_id: str, request: Request):
    """Get specific content by ID. Costs 1 credit."""
    user = await get_user_from_api_key(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    await check_credits_or_block(user.user_id, CREDIT_COSTS["content_extract"], "content_extract")
    content = await db.crawled_content.find_one({"content_id": content_id}, {"_id": 0})
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    return content


@router.post("/crawl")
async def crawl_website(crawl_request: CrawlRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    """Crawl a URL. Costs 1 credit."""
    await check_credits_or_block(user.user_id, CREDIT_COSTS["crawl"], "crawl")
    data = await crawl_url(crawl_request.url)
    content_id = f"content_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)

    existing = await db.crawled_content.find_one({"url": data["url"]}, {"_id": 0})
    if existing:
        content_id = existing["content_id"]

    content = CrawledContent(
        content_id=content_id, url=data["url"], title=data["title"],
        description=data["description"], content=data["content"],
        structured_data=data["structured_data"], domain=data["domain"],
        crawled_at=now, last_updated=now
    )
    doc = content.model_dump()
    doc["crawled_at"] = doc["crawled_at"].isoformat()
    doc["last_updated"] = doc["last_updated"].isoformat()
    await db.crawled_content.update_one({"url": data["url"]}, {"$set": doc}, upsert=True)

    content_hash = hashlib.md5(data["content"].encode()).hexdigest()
    history_entry = {
        "history_id": f"hist_{uuid.uuid4().hex[:12]}",
        "content_id": content_id, "url": data["url"], "title": data["title"],
        "content_hash": content_hash, "word_count": len(data["content"].split()),
        "status": "success", "source": "manual", "crawled_at": now.isoformat()
    }
    await db.crawl_history.insert_one(history_entry)

    event_type = "content.updated" if existing else "content.new"
    background_tasks.add_task(
        queue_webhook_delivery, event_type,
        {"content_id": content_id, "url": data["url"], "title": data["title"]},
        user.user_id
    )
    return content.model_dump()


async def process_bulk_crawl_job(job_id: str, urls: List[str], user_id: str):
    completed = 0
    failed = 0
    for url in urls:
        try:
            data = await crawl_url(url)
            content_id = f"content_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            doc = {
                "content_id": content_id, "url": data["url"], "title": data["title"],
                "description": data["description"], "content": data["content"],
                "structured_data": data["structured_data"], "domain": data["domain"],
                "crawled_at": now.isoformat(), "last_updated": now.isoformat()
            }
            await db.crawled_content.update_one({"url": data["url"]}, {"$set": doc}, upsert=True)
            completed += 1
            await db.crawl_jobs.update_one({"job_id": job_id}, {"$set": {"completed": completed, "failed": failed}})
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Bulk crawl failed for {url}: {e}")
            failed += 1
            await db.crawl_jobs.update_one({"job_id": job_id}, {"$set": {"completed": completed, "failed": failed}})

    await db.crawl_jobs.update_one(
        {"job_id": job_id},
        {"$set": {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    await queue_webhook_delivery(
        "crawl.bulk_complete",
        {"job_id": job_id, "completed": completed, "failed": failed, "total": len(urls)},
        user_id
    )


@router.post("/crawl/bulk", response_model=BulkCrawlResponse)
async def bulk_crawl(request: BulkCrawlRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    if len(request.urls) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 URLs per request")
    if len(request.urls) == 0:
        raise HTTPException(status_code=400, detail="At least one URL required")
    total_cost = len(request.urls) * CREDIT_COSTS["bulk_crawl_per_url"]
    await check_credits_or_block(user.user_id, total_cost, f"bulk_crawl_{len(request.urls)}_urls")
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    job = CrawlJob(job_id=job_id, user_id=user.user_id, urls=request.urls, status="processing")
    doc = job.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.crawl_jobs.insert_one(doc)
    background_tasks.add_task(process_bulk_crawl_job, job_id, request.urls, user.user_id)
    return BulkCrawlResponse(job_id=job_id, total_urls=len(request.urls), status="processing", message=f"Crawling {len(request.urls)} URLs in background")


@router.get("/crawl/jobs")
async def list_crawl_jobs(user: User = Depends(get_current_user)):
    return await db.crawl_jobs.find({"user_id": user.user_id}, {"_id": 0}).sort("created_at", -1).limit(20).to_list(20)


@router.get("/crawl/jobs/{job_id}")
async def get_crawl_job(job_id: str, user: User = Depends(get_current_user)):
    job = await db.crawl_jobs.find_one({"job_id": job_id, "user_id": user.user_id}, {"_id": 0})
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/crawl/schedule")
async def create_scheduled_crawl(schedule_data: ScheduledCrawlCreate, user: User = Depends(get_current_user)):
    if schedule_data.frequency not in ["hourly", "daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Frequency must be hourly, daily, or weekly")
    now = datetime.now(timezone.utc)
    if schedule_data.frequency == "hourly":
        next_crawl = now + timedelta(hours=1)
    elif schedule_data.frequency == "daily":
        next_crawl = now + timedelta(days=1)
    else:
        next_crawl = now + timedelta(weeks=1)
    schedule = ScheduledCrawl(
        schedule_id=f"sched_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id, url=schedule_data.url,
        frequency=schedule_data.frequency, next_crawl=next_crawl
    )
    doc = schedule.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["next_crawl"] = doc["next_crawl"].isoformat() if doc["next_crawl"] else None
    existing = await db.scheduled_crawls.find_one({"user_id": user.user_id, "url": schedule_data.url})
    if existing:
        raise HTTPException(status_code=400, detail="URL already scheduled")
    await db.scheduled_crawls.insert_one(doc)
    try:
        data = await crawl_url(schedule_data.url)
        content_id = f"content_{uuid.uuid4().hex[:12]}"
        content_doc = {
            "content_id": content_id, "url": data["url"], "title": data["title"],
            "description": data["description"], "content": data["content"],
            "structured_data": data["structured_data"], "domain": data["domain"],
            "crawled_at": now.isoformat(), "last_updated": now.isoformat()
        }
        await db.crawled_content.update_one({"url": data["url"]}, {"$set": content_doc}, upsert=True)
        await db.scheduled_crawls.update_one({"schedule_id": schedule.schedule_id}, {"$set": {"last_crawl": now.isoformat()}})
    except Exception as e:
        logger.warning(f"Initial crawl failed for scheduled URL: {e}")
    return schedule.model_dump()


@router.get("/crawl/schedule")
async def list_scheduled_crawls(user: User = Depends(get_current_user)):
    return await db.scheduled_crawls.find({"user_id": user.user_id}, {"_id": 0}).to_list(100)


@router.delete("/crawl/schedule/{schedule_id}")
async def delete_scheduled_crawl(schedule_id: str, user: User = Depends(get_current_user)):
    result = await db.scheduled_crawls.delete_one({"schedule_id": schedule_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule deleted"}


@router.put("/crawl/schedule/{schedule_id}/toggle")
async def toggle_scheduled_crawl(schedule_id: str, user: User = Depends(get_current_user)):
    schedule = await db.scheduled_crawls.find_one({"schedule_id": schedule_id, "user_id": user.user_id})
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    new_status = not schedule.get("is_active", True)
    await db.scheduled_crawls.update_one({"schedule_id": schedule_id}, {"$set": {"is_active": new_status}})
    return {"schedule_id": schedule_id, "is_active": new_status}


# History endpoints — stats MUST be before {content_id} to avoid path conflict
@router.get("/crawl/history/stats")
async def get_crawl_history_stats(user: User = Depends(get_current_user)):
    total = await db.crawl_history.count_documents({})
    success = await db.crawl_history.count_documents({"status": "success"})
    failed = await db.crawl_history.count_documents({"status": "failed"})
    recent = await db.crawl_history.find({}, {"_id": 0}).sort("crawled_at", -1).limit(5).to_list(5)
    unique_domains = await db.crawled_content.distinct("domain")
    total_content = await db.crawled_content.count_documents({})
    return {
        "total_crawls": total, "successful": success, "failed": failed,
        "success_rate": round((success / total * 100) if total > 0 else 0, 2),
        "unique_domains": len(unique_domains), "total_content": total_content,
        "recent": recent
    }


@router.get("/crawl/history")
async def list_crawl_history(user: User = Depends(get_current_user), limit: int = 50):
    return await db.crawl_history.find({}, {"_id": 0}).sort("crawled_at", -1).limit(limit).to_list(limit)


@router.get("/crawl/history/{content_id}")
async def get_content_crawl_history(content_id: str, user: User = Depends(get_current_user)):
    return await db.crawl_history.find({"content_id": content_id}, {"_id": 0}).sort("crawled_at", -1).to_list(50)


async def run_scheduled_crawls():
    """Background task to run scheduled crawls"""
    while True:
        try:
            now = datetime.now(timezone.utc)
            due_schedules = await db.scheduled_crawls.find({
                "is_active": True,
                "next_crawl": {"$lte": now.isoformat()}
            }).to_list(50)

            for schedule in due_schedules:
                try:
                    data = await crawl_url(schedule["url"])
                    content_id = f"content_{uuid.uuid4().hex[:12]}"
                    content_doc = {
                        "content_id": content_id, "url": data["url"], "title": data["title"],
                        "description": data["description"], "content": data["content"],
                        "structured_data": data["structured_data"], "domain": data["domain"],
                        "crawled_at": now.isoformat(), "last_updated": now.isoformat()
                    }
                    await db.crawled_content.update_one({"url": data["url"]}, {"$set": content_doc}, upsert=True)
                    freq = schedule.get("frequency", "daily")
                    if freq == "hourly":
                        next_crawl = now + timedelta(hours=1)
                    elif freq == "daily":
                        next_crawl = now + timedelta(days=1)
                    else:
                        next_crawl = now + timedelta(weeks=1)
                    await db.scheduled_crawls.update_one(
                        {"schedule_id": schedule["schedule_id"]},
                        {"$set": {"last_crawl": now.isoformat(), "next_crawl": next_crawl.isoformat()}}
                    )
                    await queue_webhook_delivery(
                        "content.updated",
                        {"url": schedule["url"], "title": data["title"], "scheduled": True},
                        schedule["user_id"]
                    )
                except Exception as e:
                    logger.error(f"Scheduled crawl failed for {schedule['url']}: {e}")
                await asyncio.sleep(1)
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"Scheduled crawl runner error: {e}")
            await asyncio.sleep(60)
