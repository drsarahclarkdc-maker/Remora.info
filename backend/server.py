from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import secrets
import hashlib
import aiohttp
import json
import httpx
import asyncio
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Import from extracted modules
from app.database import db, client
from app.models import (
    User, UserSession, APIKey, APIKeyCreate, APIKeyResponse, APIKeyCreatedResponse,
    Agent, AgentCreate, AgentUpdate,
    Webhook, WebhookCreate, WebhookUpdate, WebhookDelivery,
    UsageRecord, SearchQuery, SearchResult, CrawledContent,
    CrawlRequest, BulkCrawlRequest, BulkCrawlResponse, CrawlJob,
    ScheduledCrawl, ScheduledCrawlCreate,
    WebhookDeliveryLog, CrawlHistory, ContentSource, ContentSourceCreate, ContentSourceUpdate,
    Organization, OrganizationCreate, OrganizationMember, OrganizationInvite, InviteMemberRequest,
    CrawlRule, CrawlRuleCreate, CrawlRuleUpdate,
    SearchRankingConfig, SearchRankingConfigCreate,
    CheckoutRequest,
    PLANS, CREDIT_COSTS,
)
from app.auth import (
    get_current_user, get_user_from_api_key, record_usage,
    get_user_credits, deduct_credits, check_credits_or_block,
)
from app.crawler import crawl_url, queue_webhook_delivery, process_webhook_queue

# Create the main app
app = FastAPI(title="Remora API", description="API-first search engine for AI agents")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Auth Routes ====================

@api_router.post("/auth/session")
async def create_session(request: Request, response: Response):
    """Exchange session_id from Emergent Auth for session token"""
    try:
        body = await request.json()
        session_id = body.get("session_id")
    except:
        raise HTTPException(status_code=400, detail="Invalid request body")
    
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")
    
    async with aiohttp.ClientSession() as http_session:
        async with http_session.get(
            "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
            headers={"X-Session-ID": session_id}
        ) as resp:
            if resp.status != 200:
                raise HTTPException(status_code=401, detail="Invalid session_id")
            auth_data = await resp.json()
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    session_token = auth_data.get("session_token")
    
    existing_user = await db.users.find_one(
        {"email": auth_data["email"]},
        {"_id": 0}
    )
    
    if existing_user:
        user_id = existing_user["user_id"]
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": auth_data.get("name", existing_user.get("name")),
                "picture": auth_data.get("picture", existing_user.get("picture"))
            }}
        )
    else:
        user = User(
            user_id=user_id,
            email=auth_data["email"],
            name=auth_data.get("name", "User"),
            picture=auth_data.get("picture")
        )
        doc = user.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.users.insert_one(doc)
    
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    session_doc = session.model_dump()
    session_doc["expires_at"] = session_doc["expires_at"].isoformat()
    session_doc["created_at"] = session_doc["created_at"].isoformat()
    
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.user_sessions.insert_one(session_doc)
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60
    )
    
    user_doc = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    if isinstance(user_doc.get("created_at"), str):
        user_doc["created_at"] = datetime.fromisoformat(user_doc["created_at"])
    
    return user_doc

@api_router.get("/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return user.model_dump()

@api_router.post("/auth/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_many({"session_token": session_token})
    
    response.delete_cookie(key="session_token", path="/")
    return {"message": "Logged out"}

# ==================== API Key Routes ====================

@api_router.get("/keys", response_model=List[APIKeyResponse])
async def list_api_keys(user: User = Depends(get_current_user)):
    """List all API keys for current user"""
    keys = await db.api_keys.find(
        {"user_id": user.user_id},
        {"_id": 0, "key_hash": 0}
    ).to_list(100)
    
    for key in keys:
        if isinstance(key.get("created_at"), str):
            key["created_at"] = datetime.fromisoformat(key["created_at"])
        if isinstance(key.get("last_used"), str):
            key["last_used"] = datetime.fromisoformat(key["last_used"])
    
    return keys

@api_router.post("/keys", response_model=APIKeyCreatedResponse)
async def create_api_key(key_data: APIKeyCreate, user: User = Depends(get_current_user)):
    """Create a new API key"""
    api_key = f"rmr_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    prefix = api_key[:12]
    
    key = APIKey(
        key_id=f"key_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        name=key_data.name,
        key_hash=key_hash,
        prefix=prefix
    )
    
    doc = key.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.api_keys.insert_one(doc)
    
    return APIKeyCreatedResponse(
        key_id=key.key_id,
        name=key.name,
        api_key=api_key,
        prefix=prefix,
        created_at=key.created_at
    )

@api_router.delete("/keys/{key_id}")
async def revoke_api_key(key_id: str, user: User = Depends(get_current_user)):
    """Revoke an API key"""
    result = await db.api_keys.delete_one({
        "key_id": key_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"message": "API key revoked"}

# ==================== Agent Registry Routes ====================

@api_router.get("/agents", response_model=List[Agent])
async def list_agents(user: User = Depends(get_current_user)):
    """List all agents for current user"""
    agents = await db.agents.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).to_list(100)
    
    for agent in agents:
        if isinstance(agent.get("created_at"), str):
            agent["created_at"] = datetime.fromisoformat(agent["created_at"])
        if isinstance(agent.get("updated_at"), str):
            agent["updated_at"] = datetime.fromisoformat(agent["updated_at"])
    
    return agents

@api_router.post("/agents", response_model=Agent)
async def create_agent(agent_data: AgentCreate, user: User = Depends(get_current_user)):
    """Register a new agent"""
    agent = Agent(
        agent_id=f"agent_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        **agent_data.model_dump()
    )
    
    doc = agent.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await db.agents.insert_one(doc)
    
    return agent

@api_router.put("/agents/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_data: AgentUpdate, user: User = Depends(get_current_user)):
    """Update an agent"""
    update_data = {k: v for k, v in agent_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.agents.update_one(
        {"agent_id": agent_id, "user_id": user.user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_doc = await db.agents.find_one({"agent_id": agent_id}, {"_id": 0})
    if isinstance(agent_doc.get("created_at"), str):
        agent_doc["created_at"] = datetime.fromisoformat(agent_doc["created_at"])
    if isinstance(agent_doc.get("updated_at"), str):
        agent_doc["updated_at"] = datetime.fromisoformat(agent_doc["updated_at"])
    
    return Agent(**agent_doc)

@api_router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, user: User = Depends(get_current_user)):
    """Delete an agent"""
    result = await db.agents.delete_one({
        "agent_id": agent_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": "Agent deleted"}

# ==================== Webhook Routes ====================

@api_router.get("/webhooks")
async def list_webhooks(user: User = Depends(get_current_user)):
    """List all webhooks for current user"""
    webhooks = await db.webhooks.find(
        {"user_id": user.user_id},
        {"_id": 0, "secret": 0}
    ).to_list(100)
    
    for webhook in webhooks:
        webhook["secret"] = "***"
        if isinstance(webhook.get("created_at"), str):
            webhook["created_at"] = datetime.fromisoformat(webhook["created_at"])
        if isinstance(webhook.get("last_delivery"), str):
            webhook["last_delivery"] = datetime.fromisoformat(webhook["last_delivery"])
    
    return webhooks

@api_router.post("/webhooks")
async def create_webhook(webhook_data: WebhookCreate, user: User = Depends(get_current_user)):
    """Create a new webhook subscription"""
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

@api_router.put("/webhooks/{webhook_id}")
async def update_webhook(webhook_id: str, webhook_data: WebhookUpdate, user: User = Depends(get_current_user)):
    """Update a webhook"""
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

@api_router.delete("/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, user: User = Depends(get_current_user)):
    """Delete a webhook"""
    result = await db.webhooks.delete_one({
        "webhook_id": webhook_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"message": "Webhook deleted"}

# ==================== Search API ====================

@api_router.post("/search", response_model=SearchResult)
async def agent_search(query: SearchQuery, request: Request, background_tasks: BackgroundTasks):
    """
    Agent Query API - accepts structured JSON queries, returns JSON results.
    Costs 1 credit per search.
    """
    import time
    start_time = time.time()
    
    user = await get_user_from_api_key(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Deduct 1 credit for search
    await check_credits_or_block(user.user_id, CREDIT_COSTS["search"], "search")
    
    api_key = request.headers.get("X-API-Key")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_doc = await db.api_keys.find_one({"key_hash": key_hash}, {"_id": 0})
    
    # Load ranking config if specified
    ranking_config = None
    if query.ranking_config_id:
        ranking_config = await db.ranking_configs.find_one(
            {"config_id": query.ranking_config_id, "user_id": user.user_id},
            {"_id": 0}
        )
    
    results = []
    total = 0
    
    # MongoDB text search
    try:
        await db.crawled_content.create_index([("title", "text"), ("content", "text"), ("description", "text")])
        
        mongo_query = {"$text": {"$search": query.query}}
        if query.filters:
            mongo_query.update(query.filters)
        
        cursor = db.crawled_content.find(
            mongo_query,
            {"_id": 0, "score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(query.max_results * 3)
        
        results = await cursor.to_list(query.max_results * 3)
        total = len(results)
    except Exception as e:
        logger.warning(f"MongoDB search error: {e}")
        results = []
        total = 0
    
    # Apply advanced ranking
    if results:
        now = datetime.now(timezone.utc)
        
        # Get boost settings
        boost_domains = query.boost_domains or (ranking_config.get("boosted_domains", []) if ranking_config else [])
        penalize_domains = ranking_config.get("penalized_domains", []) if ranking_config else []
        prefer_types = query.prefer_types or (ranking_config.get("preferred_types", []) if ranking_config else [])
        domain_boost = ranking_config.get("domain_boost_factor", 1.5) if ranking_config else 1.5
        type_boost = ranking_config.get("type_boost_factor", 1.3) if ranking_config else 1.3
        recency_decay_days = ranking_config.get("recency_decay_days", 30) if ranking_config else 30
        apply_recency = query.recency_boost if query.recency_boost is not None else (ranking_config.get("recency_boost", True) if ranking_config else True)
        
        for result in results:
            score = result.get("score", 1.0) if isinstance(result.get("score"), (int, float)) else 1.0
            
            # Domain boosting
            domain = result.get("domain", "")
            if domain in boost_domains:
                score *= domain_boost
            elif domain in penalize_domains:
                score *= 0.5
            
            # Type boosting
            content_type = result.get("structured_data", {}).get("type", "")
            if content_type in prefer_types:
                score *= type_boost
            
            # Recency boosting
            if apply_recency:
                crawled_at = result.get("crawled_at") or result.get("last_updated")
                if crawled_at:
                    if isinstance(crawled_at, str):
                        try:
                            crawled_at = datetime.fromisoformat(crawled_at.replace('Z', '+00:00'))
                        except:
                            crawled_at = None
                    if crawled_at:
                        if crawled_at.tzinfo is None:
                            crawled_at = crawled_at.replace(tzinfo=timezone.utc)
                        days_old = (now - crawled_at).days
                        recency_factor = max(0, 1 - (days_old / recency_decay_days))
                        score *= (1 + recency_factor * 0.3)  # Up to 30% boost for fresh content
            
            result["_ranking_score"] = score
        
        # Sort by ranking score or recency
        if query.sort_by == "recency":
            results.sort(key=lambda x: x.get("crawled_at", ""), reverse=True)
        else:
            results.sort(key=lambda x: x.get("_ranking_score", 0), reverse=True)
        
        # Clean up and limit results
        results = results[:query.max_results]
        for result in results:
            result.pop("_ranking_score", None)
            result.pop("score", None)
    
    processing_time = int((time.time() - start_time) * 1000)
    
    # Record usage (free - just tracking)
    await record_usage(
        key_id=key_doc["key_id"],
        user_id=user.user_id,
        endpoint="/api/search",
        method="POST",
        status_code=200,
        response_time_ms=processing_time
    )
    
    # Queue webhook notifications
    background_tasks.add_task(
        queue_webhook_delivery,
        "search.complete",
        {"query": query.query, "total": total, "processing_time_ms": processing_time},
        user.user_id
    )
    
    return SearchResult(
        results=results,
        total=total,
        query=query.query,
        processing_time_ms=processing_time
    )

# ==================== Content & Crawler Routes ====================

@api_router.get("/content")
async def list_content(user: User = Depends(get_current_user), limit: int = 50):
    """List crawled content"""
    content = await db.crawled_content.find(
        {},
        {"_id": 0}
    ).sort("crawled_at", -1).limit(limit).to_list(limit)
    
    for item in content:
        if isinstance(item.get("crawled_at"), str):
            item["crawled_at"] = datetime.fromisoformat(item["crawled_at"])
        if isinstance(item.get("last_updated"), str):
            item["last_updated"] = datetime.fromisoformat(item["last_updated"])
    
    return content

@api_router.get("/content/{content_id}")
async def get_content(content_id: str, request: Request):
    """Get specific content by ID (API key auth for agents). Costs 1 credit."""
    user = await get_user_from_api_key(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Deduct 1 credit for content extract
    await check_credits_or_block(user.user_id, CREDIT_COSTS["content_extract"], "content_extract")
    
    content = await db.crawled_content.find_one(
        {"content_id": content_id},
        {"_id": 0}
    )
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return content

@api_router.post("/crawl")
async def crawl_website(crawl_request: CrawlRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    """Crawl a URL and extract structured data. Costs 1 credit."""
    # Deduct 1 credit for crawl
    await check_credits_or_block(user.user_id, CREDIT_COSTS["crawl"], "crawl")
    
    data = await crawl_url(crawl_request.url)
    
    content_id = f"content_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Check if URL already exists
    existing = await db.crawled_content.find_one({"url": data["url"]}, {"_id": 0})
    if existing:
        content_id = existing["content_id"]
    
    content = CrawledContent(
        content_id=content_id,
        url=data["url"],
        title=data["title"],
        description=data["description"],
        content=data["content"],
        structured_data=data["structured_data"],
        domain=data["domain"],
        crawled_at=now,
        last_updated=now
    )
    
    doc = content.model_dump()
    doc["crawled_at"] = doc["crawled_at"].isoformat()
    doc["last_updated"] = doc["last_updated"].isoformat()
    
    # Upsert based on URL
    await db.crawled_content.update_one(
        {"url": data["url"]},
        {"$set": doc},
        upsert=True
    )
    
    # Save crawl history
    content_hash = hashlib.md5(data["content"].encode()).hexdigest()
    history_entry = {
        "history_id": f"hist_{uuid.uuid4().hex[:12]}",
        "content_id": content_id,
        "url": data["url"],
        "title": data["title"],
        "content_hash": content_hash,
        "word_count": len(data["content"].split()),
        "status": "success",
        "source": "manual",
        "crawled_at": now.isoformat()
    }
    await db.crawl_history.insert_one(history_entry)
    
    # Queue webhook notification
    event_type = "content.updated" if existing else "content.new"
    background_tasks.add_task(
        queue_webhook_delivery,
        event_type,
        {"content_id": content_id, "url": data["url"], "title": data["title"]},
        user.user_id
    )
    
    return content.model_dump()

# ==================== Bulk Crawl & Scheduled Crawl ====================

async def process_bulk_crawl_job(job_id: str, urls: List[str], user_id: str):
    """Background task to process bulk crawl jobs"""
    completed = 0
    failed = 0
    
    for url in urls:
        try:
            data = await crawl_url(url)
            content_id = f"content_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc)
            
            doc = {
                "content_id": content_id,
                "url": data["url"],
                "title": data["title"],
                "description": data["description"],
                "content": data["content"],
                "structured_data": data["structured_data"],
                "domain": data["domain"],
                "crawled_at": now.isoformat(),
                "last_updated": now.isoformat()
            }
            
            await db.crawled_content.update_one(
                {"url": data["url"]},
                {"$set": doc},
                upsert=True
            )
            
            completed += 1
            
            # Update job progress
            await db.crawl_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"completed": completed, "failed": failed}}
            )
            
            # Small delay to be polite to servers
            await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Bulk crawl failed for {url}: {e}")
            failed += 1
            await db.crawl_jobs.update_one(
                {"job_id": job_id},
                {"$set": {"completed": completed, "failed": failed}}
            )
    
    # Mark job as completed
    await db.crawl_jobs.update_one(
        {"job_id": job_id},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Queue webhook
    await queue_webhook_delivery(
        "crawl.bulk_complete",
        {"job_id": job_id, "completed": completed, "failed": failed, "total": len(urls)},
        user_id
    )
    
    logger.info(f"Bulk crawl job {job_id} completed: {completed} success, {failed} failed")

@api_router.post("/crawl/bulk", response_model=BulkCrawlResponse)
async def bulk_crawl(request: BulkCrawlRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    """Submit multiple URLs for crawling. Costs 1 credit per URL."""
    if len(request.urls) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 URLs per request")
    
    if len(request.urls) == 0:
        raise HTTPException(status_code=400, detail="At least one URL required")
    
    # Deduct credits for all URLs upfront
    total_cost = len(request.urls) * CREDIT_COSTS["bulk_crawl_per_url"]
    await check_credits_or_block(user.user_id, total_cost, f"bulk_crawl_{len(request.urls)}_urls")
    
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    
    job = CrawlJob(
        job_id=job_id,
        user_id=user.user_id,
        urls=request.urls,
        status="processing"
    )
    
    doc = job.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.crawl_jobs.insert_one(doc)
    
    # Start background processing
    background_tasks.add_task(process_bulk_crawl_job, job_id, request.urls, user.user_id)
    
    return BulkCrawlResponse(
        job_id=job_id,
        total_urls=len(request.urls),
        status="processing",
        message=f"Crawling {len(request.urls)} URLs in background"
    )

@api_router.get("/crawl/jobs")
async def list_crawl_jobs(user: User = Depends(get_current_user)):
    """List all crawl jobs for current user"""
    jobs = await db.crawl_jobs.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    
    return jobs

@api_router.get("/crawl/jobs/{job_id}")
async def get_crawl_job(job_id: str, user: User = Depends(get_current_user)):
    """Get status of a specific crawl job"""
    job = await db.crawl_jobs.find_one(
        {"job_id": job_id, "user_id": user.user_id},
        {"_id": 0}
    )
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

# ==================== Scheduled Crawls ====================

@api_router.post("/crawl/schedule")
async def create_scheduled_crawl(schedule_data: ScheduledCrawlCreate, user: User = Depends(get_current_user)):
    """Schedule a URL for automatic periodic crawling"""
    if schedule_data.frequency not in ["hourly", "daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Frequency must be hourly, daily, or weekly")
    
    # Calculate next crawl time
    now = datetime.now(timezone.utc)
    if schedule_data.frequency == "hourly":
        next_crawl = now + timedelta(hours=1)
    elif schedule_data.frequency == "daily":
        next_crawl = now + timedelta(days=1)
    else:  # weekly
        next_crawl = now + timedelta(weeks=1)
    
    schedule = ScheduledCrawl(
        schedule_id=f"sched_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        url=schedule_data.url,
        frequency=schedule_data.frequency,
        next_crawl=next_crawl
    )
    
    doc = schedule.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["next_crawl"] = doc["next_crawl"].isoformat() if doc["next_crawl"] else None
    
    # Check for duplicate
    existing = await db.scheduled_crawls.find_one({
        "user_id": user.user_id,
        "url": schedule_data.url
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="URL already scheduled")
    
    await db.scheduled_crawls.insert_one(doc)
    
    # Do initial crawl
    try:
        data = await crawl_url(schedule_data.url)
        content_id = f"content_{uuid.uuid4().hex[:12]}"
        
        content_doc = {
            "content_id": content_id,
            "url": data["url"],
            "title": data["title"],
            "description": data["description"],
            "content": data["content"],
            "structured_data": data["structured_data"],
            "domain": data["domain"],
            "crawled_at": now.isoformat(),
            "last_updated": now.isoformat()
        }
        
        await db.crawled_content.update_one(
            {"url": data["url"]},
            {"$set": content_doc},
            upsert=True
        )
        
        await db.scheduled_crawls.update_one(
            {"schedule_id": schedule.schedule_id},
            {"$set": {"last_crawl": now.isoformat()}}
        )
    except Exception as e:
        logger.warning(f"Initial crawl failed for scheduled URL: {e}")
    
    return schedule.model_dump()

@api_router.get("/crawl/schedule")
async def list_scheduled_crawls(user: User = Depends(get_current_user)):
    """List all scheduled crawls for current user"""
    schedules = await db.scheduled_crawls.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).to_list(100)
    
    return schedules

@api_router.delete("/crawl/schedule/{schedule_id}")
async def delete_scheduled_crawl(schedule_id: str, user: User = Depends(get_current_user)):
    """Delete a scheduled crawl"""
    result = await db.scheduled_crawls.delete_one({
        "schedule_id": schedule_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {"message": "Schedule deleted"}

@api_router.put("/crawl/schedule/{schedule_id}/toggle")
async def toggle_scheduled_crawl(schedule_id: str, user: User = Depends(get_current_user)):
    """Toggle a scheduled crawl on/off"""
    schedule = await db.scheduled_crawls.find_one({
        "schedule_id": schedule_id,
        "user_id": user.user_id
    })
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    new_status = not schedule.get("is_active", True)
    
    await db.scheduled_crawls.update_one(
        {"schedule_id": schedule_id},
        {"$set": {"is_active": new_status}}
    )
    
    return {"schedule_id": schedule_id, "is_active": new_status}

# Background task to run scheduled crawls
async def run_scheduled_crawls():
    """Check and execute due scheduled crawls"""
    while True:
        try:
            now = datetime.now(timezone.utc)
            
            # Find due schedules
            due_schedules = await db.scheduled_crawls.find({
                "is_active": True,
                "next_crawl": {"$lte": now.isoformat()}
            }).to_list(50)
            
            for schedule in due_schedules:
                try:
                    data = await crawl_url(schedule["url"])
                    content_id = f"content_{uuid.uuid4().hex[:12]}"
                    
                    content_doc = {
                        "content_id": content_id,
                        "url": data["url"],
                        "title": data["title"],
                        "description": data["description"],
                        "content": data["content"],
                        "structured_data": data["structured_data"],
                        "domain": data["domain"],
                        "crawled_at": now.isoformat(),
                        "last_updated": now.isoformat()
                    }
                    
                    await db.crawled_content.update_one(
                        {"url": data["url"]},
                        {"$set": content_doc},
                        upsert=True
                    )
                    
                    # Calculate next crawl
                    freq = schedule.get("frequency", "daily")
                    if freq == "hourly":
                        next_crawl = now + timedelta(hours=1)
                    elif freq == "daily":
                        next_crawl = now + timedelta(days=1)
                    else:
                        next_crawl = now + timedelta(weeks=1)
                    
                    await db.scheduled_crawls.update_one(
                        {"schedule_id": schedule["schedule_id"]},
                        {"$set": {
                            "last_crawl": now.isoformat(),
                            "next_crawl": next_crawl.isoformat()
                        }}
                    )
                    
                    # Queue webhook
                    await queue_webhook_delivery(
                        "content.updated",
                        {"url": schedule["url"], "title": data["title"], "scheduled": True},
                        schedule["user_id"]
                    )
                    
                    logger.info(f"Scheduled crawl completed: {schedule['url']}")
                    
                except Exception as e:
                    logger.error(f"Scheduled crawl failed for {schedule['url']}: {e}")
                
                await asyncio.sleep(1)  # Rate limiting
            
            await asyncio.sleep(60)  # Check every minute
            
        except Exception as e:
            logger.error(f"Scheduled crawl runner error: {e}")
            await asyncio.sleep(60)

# ==================== Webhook Delivery Logs ====================

@api_router.get("/webhooks/deliveries")
async def list_webhook_deliveries(user: User = Depends(get_current_user), limit: int = 50):
    """List webhook delivery logs for current user"""
    logs = await db.webhook_delivery_logs.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return logs

@api_router.get("/webhooks/{webhook_id}/deliveries")
async def list_webhook_deliveries_by_id(webhook_id: str, user: User = Depends(get_current_user), limit: int = 50):
    """List delivery logs for a specific webhook"""
    # Verify webhook belongs to user
    webhook = await db.webhooks.find_one({"webhook_id": webhook_id, "user_id": user.user_id})
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    logs = await db.webhook_delivery_logs.find(
        {"webhook_id": webhook_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return logs

@api_router.get("/webhooks/deliveries/stats")
async def get_webhook_delivery_stats(user: User = Depends(get_current_user)):
    """Get webhook delivery statistics"""
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

# ==================== Content Sources ====================

@api_router.get("/sources")
async def list_content_sources(user: User = Depends(get_current_user)):
    """List all content sources for current user"""
    sources = await db.content_sources.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return sources

@api_router.post("/sources")
async def create_content_source(source_data: ContentSourceCreate, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    """Create a new content source"""
    parsed = urlparse(source_data.url)
    domain = parsed.netloc
    
    # Check for duplicate
    existing = await db.content_sources.find_one({
        "user_id": user.user_id,
        "url": source_data.url
    })
    if existing:
        raise HTTPException(status_code=400, detail="Source URL already exists")
    
    source = ContentSource(
        source_id=f"src_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        name=source_data.name,
        url=source_data.url,
        domain=domain,
        crawl_frequency=source_data.crawl_frequency
    )
    
    doc = source.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.content_sources.insert_one(doc)
    
    # Do initial crawl
    try:
        data = await crawl_url(source_data.url)
        content_id = f"content_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        content_doc = {
            "content_id": content_id,
            "url": data["url"],
            "title": data["title"],
            "description": data["description"],
            "content": data["content"],
            "structured_data": data["structured_data"],
            "domain": data["domain"],
            "source_id": source.source_id,
            "crawled_at": now.isoformat(),
            "last_updated": now.isoformat()
        }
        
        await db.crawled_content.update_one(
            {"url": data["url"]},
            {"$set": content_doc},
            upsert=True
        )
        
        # Save crawl history
        content_hash = hashlib.md5(data["content"].encode()).hexdigest()
        history_entry = {
            "history_id": f"hist_{uuid.uuid4().hex[:12]}",
            "content_id": content_id,
            "url": data["url"],
            "title": data["title"],
            "content_hash": content_hash,
            "word_count": len(data["content"].split()),
            "status": "success",
            "source": "source",
            "crawled_at": now.isoformat()
        }
        await db.crawl_history.insert_one(history_entry)
        
        await db.content_sources.update_one(
            {"source_id": source.source_id},
            {"$set": {
                "last_crawl": now.isoformat(),
                "last_status": "success",
                "content_count": 1
            }}
        )
        
    except Exception as e:
        await db.content_sources.update_one(
            {"source_id": source.source_id},
            {"$set": {"last_status": f"failed: {str(e)[:100]}"}}
        )
    
    # If scheduled, also create a scheduled crawl
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
            "user_id": user.user_id,
            "url": source_data.url,
            "frequency": source_data.crawl_frequency,
            "is_active": True,
            "source_id": source.source_id,
            "next_crawl": next_crawl.isoformat(),
            "created_at": now.isoformat()
        }
        await db.scheduled_crawls.insert_one(schedule_doc)
    
    return source.model_dump()

@api_router.put("/sources/{source_id}")
async def update_content_source(source_id: str, source_data: ContentSourceUpdate, user: User = Depends(get_current_user)):
    """Update a content source"""
    update_data = {k: v for k, v in source_data.model_dump().items() if v is not None}
    
    result = await db.content_sources.update_one(
        {"source_id": source_id, "user_id": user.user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Source not found")
    
    source = await db.content_sources.find_one({"source_id": source_id}, {"_id": 0})
    return source

@api_router.delete("/sources/{source_id}")
async def delete_content_source(source_id: str, user: User = Depends(get_current_user)):
    """Delete a content source"""
    result = await db.content_sources.delete_one({
        "source_id": source_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # Also delete associated scheduled crawls
    await db.scheduled_crawls.delete_many({"source_id": source_id})
    
    return {"message": "Source deleted"}

@api_router.post("/sources/{source_id}/crawl")
async def crawl_content_source(source_id: str, user: User = Depends(get_current_user)):
    """Manually trigger a crawl for a content source"""
    source = await db.content_sources.find_one({
        "source_id": source_id,
        "user_id": user.user_id
    })
    
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    try:
        data = await crawl_url(source["url"])
        content_id = f"content_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        # Check if URL exists
        existing = await db.crawled_content.find_one({"url": data["url"]}, {"_id": 0})
        if existing:
            content_id = existing["content_id"]
        
        content_doc = {
            "content_id": content_id,
            "url": data["url"],
            "title": data["title"],
            "description": data["description"],
            "content": data["content"],
            "structured_data": data["structured_data"],
            "domain": data["domain"],
            "source_id": source_id,
            "crawled_at": now.isoformat(),
            "last_updated": now.isoformat()
        }
        
        await db.crawled_content.update_one(
            {"url": data["url"]},
            {"$set": content_doc},
            upsert=True
        )
        
        # Save crawl history
        content_hash = hashlib.md5(data["content"].encode()).hexdigest()
        history_entry = {
            "history_id": f"hist_{uuid.uuid4().hex[:12]}",
            "content_id": content_id,
            "url": data["url"],
            "title": data["title"],
            "content_hash": content_hash,
            "word_count": len(data["content"].split()),
            "status": "success",
            "source": "manual",
            "crawled_at": now.isoformat()
        }
        await db.crawl_history.insert_one(history_entry)
        
        await db.content_sources.update_one(
            {"source_id": source_id},
            {"$set": {
                "last_crawl": now.isoformat(),
                "last_status": "success"
            },
            "$inc": {"content_count": 1 if not existing else 0}}
        )
        
        return {"status": "success", "content_id": content_id, "title": data["title"]}
        
    except Exception as e:
        await db.content_sources.update_one(
            {"source_id": source_id},
            {"$set": {"last_status": f"failed: {str(e)[:100]}"}}
        )
        raise HTTPException(status_code=400, detail=f"Crawl failed: {str(e)}")

# ==================== Crawl History ====================

@api_router.get("/crawl/history")
async def list_crawl_history(user: User = Depends(get_current_user), limit: int = 50):
    """List crawl history"""
    # Get user's content IDs first
    history = await db.crawl_history.find(
        {},
        {"_id": 0}
    ).sort("crawled_at", -1).limit(limit).to_list(limit)
    
    return history

@api_router.get("/crawl/history/{content_id}")
async def get_crawl_history_for_content(content_id: str, user: User = Depends(get_current_user)):
    """Get crawl history for a specific content"""
    history = await db.crawl_history.find(
        {"content_id": content_id},
        {"_id": 0}
    ).sort("crawled_at", -1).to_list(50)
    
    return history

@api_router.get("/crawl/history/stats")
async def get_crawl_history_stats(user: User = Depends(get_current_user)):
    """Get crawl history statistics"""
    total = await db.crawl_history.count_documents({})
    success = await db.crawl_history.count_documents({"status": "success"})
    failed = await db.crawl_history.count_documents({"status": "failed"})
    
    # Get crawls by source type
    by_source = {}
    for source in ["manual", "scheduled", "bulk", "source"]:
        count = await db.crawl_history.count_documents({"source": source})
        by_source[source] = count
    
    # Get recent crawl counts by day
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_counts = []
    for i in range(7):
        day_start = today - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        count = await db.crawl_history.count_documents({
            "crawled_at": {
                "$gte": day_start.isoformat(),
                "$lt": day_end.isoformat()
            }
        })
        daily_counts.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "crawls": count
        })
    
    return {
        "total": total,
        "success": success,
        "failed": failed,
        "success_rate": round((success / total * 100) if total > 0 else 0, 2),
        "by_source": by_source,
        "daily_counts": list(reversed(daily_counts))
    }

# ==================== Usage & Analytics Routes ====================

@api_router.get("/usage/stats")
async def get_usage_stats(user: User = Depends(get_current_user)):
    """Get usage statistics for current user - FREE for everyone"""
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

@api_router.get("/usage/recent")
async def get_recent_usage(user: User = Depends(get_current_user), limit: int = 20):
    """Get recent API usage records"""
    records = await db.usage_records.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    for record in records:
        if isinstance(record.get("timestamp"), str):
            record["timestamp"] = datetime.fromisoformat(record["timestamp"])
    
    return records

# ==================== Crawl Rules ====================

@api_router.get("/rules")
async def list_crawl_rules(user: User = Depends(get_current_user)):
    """List all crawl rules for current user"""
    rules = await db.crawl_rules.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return rules

@api_router.post("/rules")
async def create_crawl_rule(rule_data: CrawlRuleCreate, user: User = Depends(get_current_user)):
    """Create a custom crawl rule for a domain"""
    # Check for existing rule for this domain
    existing = await db.crawl_rules.find_one({
        "user_id": user.user_id,
        "domain": rule_data.domain
    })
    if existing:
        raise HTTPException(status_code=400, detail="Rule for this domain already exists")
    
    rule = CrawlRule(
        rule_id=f"rule_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        **rule_data.model_dump()
    )
    
    doc = rule.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await db.crawl_rules.insert_one(doc)
    
    return rule.model_dump()

@api_router.get("/rules/{rule_id}")
async def get_crawl_rule(rule_id: str, user: User = Depends(get_current_user)):
    """Get a specific crawl rule"""
    rule = await db.crawl_rules.find_one(
        {"rule_id": rule_id, "user_id": user.user_id},
        {"_id": 0}
    )
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule

@api_router.put("/rules/{rule_id}")
async def update_crawl_rule(rule_id: str, rule_data: CrawlRuleUpdate, user: User = Depends(get_current_user)):
    """Update a crawl rule"""
    update_data = {k: v for k, v in rule_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    result = await db.crawl_rules.update_one(
        {"rule_id": rule_id, "user_id": user.user_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule = await db.crawl_rules.find_one({"rule_id": rule_id}, {"_id": 0})
    return rule

@api_router.delete("/rules/{rule_id}")
async def delete_crawl_rule(rule_id: str, user: User = Depends(get_current_user)):
    """Delete a crawl rule"""
    result = await db.crawl_rules.delete_one({
        "rule_id": rule_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return {"message": "Rule deleted"}

@api_router.get("/rules/domain/{domain}")
async def get_rule_for_domain(domain: str, user: User = Depends(get_current_user)):
    """Get crawl rule for a specific domain"""
    rule = await db.crawl_rules.find_one(
        {"user_id": user.user_id, "domain": domain, "is_active": True},
        {"_id": 0}
    )
    return rule

# ==================== Search Ranking Configs ====================

@api_router.get("/ranking")
async def list_ranking_configs(user: User = Depends(get_current_user)):
    """List all ranking configurations"""
    configs = await db.ranking_configs.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return configs

@api_router.post("/ranking")
async def create_ranking_config(config_data: SearchRankingConfigCreate, user: User = Depends(get_current_user)):
    """Create a search ranking configuration"""
    # If setting as default, unset other defaults
    if config_data.is_default:
        await db.ranking_configs.update_many(
            {"user_id": user.user_id},
            {"$set": {"is_default": False}}
        )
    
    config = SearchRankingConfig(
        config_id=f"rank_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        **config_data.model_dump()
    )
    
    doc = config.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.ranking_configs.insert_one(doc)
    
    return config.model_dump()

@api_router.get("/ranking/{config_id}")
async def get_ranking_config(config_id: str, user: User = Depends(get_current_user)):
    """Get a specific ranking configuration"""
    config = await db.ranking_configs.find_one(
        {"config_id": config_id, "user_id": user.user_id},
        {"_id": 0}
    )
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@api_router.put("/ranking/{config_id}")
async def update_ranking_config(config_id: str, config_data: SearchRankingConfigCreate, user: User = Depends(get_current_user)):
    """Update a search ranking configuration"""
    existing = await db.ranking_configs.find_one({"config_id": config_id, "user_id": user.user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Config not found")
    
    if config_data.is_default:
        await db.ranking_configs.update_many(
            {"user_id": user.user_id, "config_id": {"$ne": config_id}},
            {"$set": {"is_default": False}}
        )
    
    update_data = config_data.model_dump()
    await db.ranking_configs.update_one(
        {"config_id": config_id, "user_id": user.user_id},
        {"$set": update_data}
    )
    
    updated = await db.ranking_configs.find_one({"config_id": config_id}, {"_id": 0})
    return updated

@api_router.delete("/ranking/{config_id}")
async def delete_ranking_config(config_id: str, user: User = Depends(get_current_user)):
    """Delete a ranking configuration"""
    result = await db.ranking_configs.delete_one({
        "config_id": config_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Config not found")
    
    return {"message": "Config deleted"}

# ==================== Organizations & Teams ====================

def generate_slug(name: str) -> str:
    """Generate a URL-safe slug from name"""
    import re
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug[:50]

@api_router.get("/orgs")
async def list_organizations(user: User = Depends(get_current_user)):
    """List organizations the user belongs to"""
    # Get memberships
    memberships = await db.org_members.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).to_list(50)
    
    org_ids = [m["org_id"] for m in memberships]
    
    # Get org details
    orgs = await db.organizations.find(
        {"org_id": {"$in": org_ids}},
        {"_id": 0}
    ).to_list(50)
    
    # Add role to each org
    role_map = {m["org_id"]: m["role"] for m in memberships}
    for org in orgs:
        org["role"] = role_map.get(org["org_id"], "member")
    
    return orgs

@api_router.post("/orgs")
async def create_organization(org_data: OrganizationCreate, user: User = Depends(get_current_user)):
    """Create a new organization"""
    slug = generate_slug(org_data.name)
    
    # Check slug uniqueness
    existing = await db.organizations.find_one({"slug": slug})
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    
    org = Organization(
        org_id=f"org_{uuid.uuid4().hex[:12]}",
        name=org_data.name,
        slug=slug,
        owner_id=user.user_id
    )
    
    doc = org.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.organizations.insert_one(doc)
    
    # Add owner as member
    member = OrganizationMember(
        member_id=f"mem_{uuid.uuid4().hex[:12]}",
        org_id=org.org_id,
        user_id=user.user_id,
        role="owner"
    )
    member_doc = member.model_dump()
    member_doc["joined_at"] = member_doc["joined_at"].isoformat()
    await db.org_members.insert_one(member_doc)
    
    result = org.model_dump()
    result["role"] = "owner"
    return result

# NOTE: Static /orgs/invites routes MUST be defined before /orgs/{org_id} to avoid path conflicts
@api_router.get("/orgs/invites/pending")
async def list_pending_invites(user: User = Depends(get_current_user)):
    """List pending invites for current user"""
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    if not user_doc:
        return []
    
    invites = await db.org_invites.find({
        "email": user_doc["email"],
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }, {"_id": 0, "token": 0}).to_list(20)
    
    # Add org details
    for invite in invites:
        org = await db.organizations.find_one({"org_id": invite["org_id"]}, {"_id": 0})
        if org:
            invite["org_name"] = org["name"]
    
    return invites

@api_router.post("/orgs/invites/{invite_id}/accept")
async def accept_invite(invite_id: str, user: User = Depends(get_current_user)):
    """Accept an organization invite"""
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    
    invite = await db.org_invites.find_one({
        "invite_id": invite_id,
        "email": user_doc["email"]
    })
    
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    
    if datetime.fromisoformat(invite["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite has expired")
    
    # Add as member
    member = OrganizationMember(
        member_id=f"mem_{uuid.uuid4().hex[:12]}",
        org_id=invite["org_id"],
        user_id=user.user_id,
        role=invite["role"]
    )
    member_doc = member.model_dump()
    member_doc["joined_at"] = member_doc["joined_at"].isoformat()
    await db.org_members.insert_one(member_doc)
    
    # Delete invite
    await db.org_invites.delete_one({"invite_id": invite_id})
    
    return {"message": "Invite accepted", "org_id": invite["org_id"]}

@api_router.get("/orgs/{org_id}")
async def get_organization(org_id: str, user: User = Depends(get_current_user)):
    """Get organization details"""
    # Check membership
    membership = await db.org_members.find_one({
        "org_id": org_id,
        "user_id": user.user_id
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    org["role"] = membership["role"]
    return org

@api_router.get("/orgs/{org_id}/members")
async def list_org_members(org_id: str, user: User = Depends(get_current_user)):
    """List organization members"""
    # Check membership
    membership = await db.org_members.find_one({
        "org_id": org_id,
        "user_id": user.user_id
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    
    members = await db.org_members.find(
        {"org_id": org_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get user details for each member
    for member in members:
        user_doc = await db.users.find_one({"user_id": member["user_id"]}, {"_id": 0})
        if user_doc:
            member["name"] = user_doc.get("name")
            member["email"] = user_doc.get("email")
            member["picture"] = user_doc.get("picture")
    
    return members

@api_router.post("/orgs/{org_id}/invite")
async def invite_member(org_id: str, invite_data: InviteMemberRequest, user: User = Depends(get_current_user)):
    """Invite a user to the organization"""
    # Check admin/owner access
    membership = await db.org_members.find_one({
        "org_id": org_id,
        "user_id": user.user_id,
        "role": {"$in": ["owner", "admin"]}
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Only admins can invite members")
    
    # Check if already a member
    existing_member = await db.org_members.find_one({
        "org_id": org_id
    })
    existing_user = await db.users.find_one({"email": invite_data.email})
    if existing_user:
        existing_membership = await db.org_members.find_one({
            "org_id": org_id,
            "user_id": existing_user["user_id"]
        })
        if existing_membership:
            raise HTTPException(status_code=400, detail="User is already a member")
    
    # Create invite
    invite = OrganizationInvite(
        invite_id=f"inv_{uuid.uuid4().hex[:12]}",
        org_id=org_id,
        email=invite_data.email,
        role=invite_data.role,
        invited_by=user.user_id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    
    doc = invite.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["expires_at"] = doc["expires_at"].isoformat()
    await db.org_invites.insert_one(doc)
    
    return {
        "invite_id": invite.invite_id,
        "email": invite.email,
        "role": invite.role,
        "expires_at": invite.expires_at.isoformat()
    }

@api_router.delete("/orgs/{org_id}/members/{member_user_id}")
async def remove_member(org_id: str, member_user_id: str, user: User = Depends(get_current_user)):
    """Remove a member from the organization"""
    # Check admin/owner access
    membership = await db.org_members.find_one({
        "org_id": org_id,
        "user_id": user.user_id,
        "role": {"$in": ["owner", "admin"]}
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Only admins can remove members")
    
    # Can't remove owner
    org = await db.organizations.find_one({"org_id": org_id})
    if org and org["owner_id"] == member_user_id:
        raise HTTPException(status_code=400, detail="Cannot remove organization owner")
    
    result = await db.org_members.delete_one({
        "org_id": org_id,
        "user_id": member_user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    
    return {"message": "Member removed"}

@api_router.delete("/orgs/{org_id}")
async def delete_organization(org_id: str, user: User = Depends(get_current_user)):
    """Delete an organization (owner only)"""
    org = await db.organizations.find_one({"org_id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if org["owner_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Only owner can delete organization")
    
    # Delete org and all members
    await db.organizations.delete_one({"org_id": org_id})
    await db.org_members.delete_many({"org_id": org_id})
    await db.org_invites.delete_many({"org_id": org_id})
    
    return {"message": "Organization deleted"}

# ==================== Billing & Stripe ====================

@api_router.get("/billing/plans")
async def list_plans():
    """List all available plans (public endpoint)"""
    return [
        {"plan_id": k, **v}
        for k, v in PLANS.items()
    ]

@api_router.get("/billing/usage")
async def get_billing_usage(user: User = Depends(get_current_user)):
    """Get current billing usage and credit balance"""
    billing = await get_user_credits(user.user_id)
    plan_info = PLANS.get(billing.get("plan", "free"), PLANS["free"])
    
    # Get recent credit usage
    recent = await db.credit_usage.find(
        {"user_id": user.user_id},
        {"_id": 0}
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

@api_router.post("/billing/checkout")
async def create_checkout(checkout_req: CheckoutRequest, request: Request, user: User = Depends(get_current_user)):
    """Create a Stripe checkout session for a plan upgrade"""
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
    
    # Create payment transaction record
    await db.payment_transactions.insert_one({
        "session_id": session.session_id,
        "user_id": user.user_id,
        "plan_id": plan_id,
        "amount": plan["price"],
        "currency": "usd",
        "credits": plan["credits"],
        "payment_status": "pending",
        "status": "initiated",
        "metadata": {
            "user_id": user.user_id,
            "plan_id": plan_id,
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    
    return {"url": session.url, "session_id": session.session_id}

@api_router.get("/billing/checkout/status/{session_id}")
async def get_checkout_status(session_id: str, request: Request, user: User = Depends(get_current_user)):
    """Poll Stripe checkout status and update billing on success"""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout
    
    # Get existing transaction first
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
    
    # Only process if not already completed (prevent double-crediting)
    if txn.get("payment_status") != "paid" and checkout_status.payment_status == "paid":
        plan_id = txn.get("plan_id", "free")
        credits = txn.get("credits", PLANS.get(plan_id, PLANS["free"])["credits"])
        now = datetime.now(timezone.utc)
        
        # Update user billing
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
        
        # Update transaction
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {"$set": {
                "payment_status": "paid",
                "status": "completed",
                "completed_at": now.isoformat(),
            }}
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

@api_router.get("/billing/transactions")
async def list_transactions(user: User = Depends(get_current_user)):
    """List payment transactions for current user"""
    txns = await db.payment_transactions.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(20).to_list(20)
    return txns

@api_router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
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
                    {"$set": {
                        "payment_status": "paid",
                        "status": "completed",
                        "completed_at": now.isoformat(),
                    }}
                )
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Stripe webhook error: {e}")
        return {"status": "error", "message": str(e)}

# ==================== Health & Status ====================

@api_router.get("/")
async def root():
    return {"message": "Remora API - Search Engine for AI Agents", "version": "1.2.0"}

@api_router.get("/docs/reference")
async def api_docs():
    """Complete API documentation with examples"""
    return {
        "name": "Remora API",
        "version": "1.2.0",
        "description": "API-first search engine for AI agents",
        "base_url": "/api",
        "authentication": {
            "type": "API Key",
            "header": "X-API-Key",
            "description": "Include your API key in the X-API-Key header for all agent endpoints",
            "example": "X-API-Key: rmr_your_api_key_here"
        },
        "endpoints": {
            "search": {
                "method": "POST",
                "path": "/api/search",
                "description": "Search for content using structured queries",
                "auth": "API Key",
                "request": {
                    "query": "string (required) - Search query",
                    "intent": "string (optional) - Query intent (documentation, tutorial, api, etc.)",
                    "filters": "object (optional) - Filter by type, language, domain",
                    "max_results": "integer (optional, default: 10) - Max results to return"
                },
                "example_request": {
                    "query": "python async patterns",
                    "intent": "documentation",
                    "filters": {"language": "python"},
                    "max_results": 5
                },
                "example_response": {
                    "results": [
                        {
                            "content_id": "content_abc123",
                            "title": "asyncio — Asynchronous I/O",
                            "url": "https://docs.python.org/3/library/asyncio.html",
                            "description": "asyncio is a library...",
                            "structured_data": {"type": "documentation", "language": "python"}
                        }
                    ],
                    "total": 42,
                    "query": "python async patterns",
                    "processing_time_ms": 23
                }
            },
            "content": {
                "method": "GET",
                "path": "/api/content/{content_id}",
                "description": "Get full content by ID",
                "auth": "API Key",
                "example_response": {
                    "content_id": "content_abc123",
                    "url": "https://example.com/page",
                    "title": "Page Title",
                    "description": "Page description",
                    "content": "Full extracted content...",
                    "structured_data": {"type": "article", "language": "en"},
                    "domain": "example.com",
                    "crawled_at": "2026-01-20T12:00:00Z"
                }
            },
            "crawl": {
                "method": "POST",
                "path": "/api/crawl",
                "description": "Crawl a single URL and extract structured data",
                "auth": "Session (Dashboard)",
                "request": {
                    "url": "string (required) - URL to crawl"
                },
                "example_request": {
                    "url": "https://fastapi.tiangolo.com/"
                }
            },
            "bulk_crawl": {
                "method": "POST",
                "path": "/api/crawl/bulk",
                "description": "Submit multiple URLs for background crawling",
                "auth": "Session (Dashboard)",
                "request": {
                    "urls": "array[string] (required) - URLs to crawl (max 100)"
                },
                "example_request": {
                    "urls": [
                        "https://docs.python.org/3/",
                        "https://react.dev/",
                        "https://tailwindcss.com/"
                    ]
                },
                "example_response": {
                    "job_id": "job_abc123",
                    "total_urls": 3,
                    "status": "processing",
                    "message": "Crawling 3 URLs in background"
                }
            },
            "crawl_job_status": {
                "method": "GET",
                "path": "/api/crawl/jobs/{job_id}",
                "description": "Check status of a bulk crawl job",
                "auth": "Session (Dashboard)",
                "example_response": {
                    "job_id": "job_abc123",
                    "status": "completed",
                    "completed": 3,
                    "failed": 0,
                    "urls": ["..."],
                    "created_at": "2026-01-20T12:00:00Z",
                    "completed_at": "2026-01-20T12:01:00Z"
                }
            },
            "schedule_crawl": {
                "method": "POST",
                "path": "/api/crawl/schedule",
                "description": "Schedule a URL for automatic periodic crawling",
                "auth": "Session (Dashboard)",
                "request": {
                    "url": "string (required) - URL to crawl",
                    "frequency": "string (required) - hourly, daily, or weekly"
                },
                "example_request": {
                    "url": "https://news.ycombinator.com/",
                    "frequency": "hourly"
                }
            },
            "agents": {
                "method": "POST",
                "path": "/api/agents",
                "description": "Register a new agent",
                "auth": "Session (Dashboard)",
                "request": {
                    "name": "string (required) - Agent name",
                    "description": "string (optional) - Agent description",
                    "capabilities": "array[string] (optional) - Agent capabilities",
                    "endpoint_url": "string (optional) - Webhook endpoint",
                    "auth_type": "string (optional) - api_key, bearer_token, oauth2, none"
                }
            },
            "webhooks": {
                "method": "POST",
                "path": "/api/webhooks",
                "description": "Subscribe to event notifications",
                "auth": "Session (Dashboard)",
                "events": [
                    "search.complete - When a search query completes",
                    "content.new - When new content is crawled",
                    "content.updated - When content is refreshed",
                    "crawl.bulk_complete - When bulk crawl job finishes"
                ],
                "webhook_payload": {
                    "headers": {
                        "X-Remora-Event": "event_name",
                        "X-Remora-Signature": "sha256_hmac_signature",
                        "X-Remora-Delivery": "delivery_id"
                    },
                    "body": "JSON payload with event data"
                }
            },
            "api_keys": {
                "method": "POST",
                "path": "/api/keys",
                "description": "Create a new API key",
                "auth": "Session (Dashboard)",
                "note": "API key is only shown once on creation"
            }
        },
        "rate_limits": {
            "current": "Free for everyone - unlimited",
            "note": "We're tracking usage to understand patterns. Paid tiers coming later."
        },
        "code_examples": {
            "python": """import requests

API_KEY = "rmr_your_api_key"
BASE_URL = "https://your-app.com/api"

# Search
response = requests.post(
    f"{BASE_URL}/search",
    headers={"X-API-Key": API_KEY},
    json={"query": "python async", "max_results": 5}
)
results = response.json()
print(f"Found {results['total']} results")
""",
            "javascript": """const API_KEY = "rmr_your_api_key";
const BASE_URL = "https://your-app.com/api";

// Search
const response = await fetch(`${BASE_URL}/search`, {
    method: "POST",
    headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    },
    body: JSON.stringify({
        query: "python async",
        max_results: 5
    })
});
const results = await response.json();
console.log(`Found ${results.total} results`);
""",
            "curl": """# Search
curl -X POST "https://your-app.com/api/search" \\
    -H "X-API-Key: rmr_your_api_key" \\
    -H "Content-Type: application/json" \\
    -d '{"query": "python async", "max_results": 5}'
"""
        }
    }

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "search": "mongodb_text_search",
        "webhook_queue": "mongodb",
        "pricing": "free_for_all"
    }

# ==================== Sample Data Seeding ====================

@api_router.post("/seed")
async def seed_sample_data():
    """Seed sample crawled content for demo purposes"""
    sample_content = [
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://docs.python.org/3/library/asyncio.html",
            "title": "asyncio — Asynchronous I/O",
            "description": "asyncio is a library to write concurrent code using async/await syntax.",
            "content": "asyncio is a library to write concurrent code using the async/await syntax. It is used as a foundation for multiple Python asynchronous frameworks that provide high-performance network and web-servers, database connection libraries, distributed task queues, etc.",
            "structured_data": {"language": "python", "type": "documentation", "topics": ["async", "concurrency", "networking"]},
            "domain": "docs.python.org",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://react.dev/learn",
            "title": "React Documentation - Quick Start",
            "description": "Learn React with official documentation and examples.",
            "content": "React lets you build user interfaces out of individual pieces called components. Create your own React components like Thumbnail, LikeButton, and Video. Then combine them into entire screens, pages, and apps.",
            "structured_data": {"language": "javascript", "type": "documentation", "topics": ["react", "frontend", "components", "ui"]},
            "domain": "react.dev",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://fastapi.tiangolo.com/",
            "title": "FastAPI - Modern Python Web Framework",
            "description": "FastAPI framework, high performance, easy to learn, fast to code, ready for production.",
            "content": "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints. Very high performance, on par with NodeJS and Go. Fast to code, fewer bugs, intuitive, easy, short, robust, standards-based.",
            "structured_data": {"language": "python", "type": "framework", "topics": ["api", "web", "backend", "rest"]},
            "domain": "fastapi.tiangolo.com",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://www.mongodb.com/docs/manual/",
            "title": "MongoDB Manual - NoSQL Database",
            "description": "MongoDB is a document database designed for ease of application development and scaling.",
            "content": "MongoDB is a document database with the scalability and flexibility that you want with the querying and indexing that you need. MongoDB stores data in flexible, JSON-like documents, meaning fields can vary from document to document.",
            "structured_data": {"language": "javascript", "type": "database", "topics": ["nosql", "database", "documents", "json"]},
            "domain": "mongodb.com",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://kubernetes.io/docs/home/",
            "title": "Kubernetes Documentation",
            "description": "Kubernetes is an open-source system for automating deployment, scaling, and management of containerized applications.",
            "content": "Kubernetes, also known as K8s, is an open-source system for automating deployment, scaling, and management of containerized applications. It groups containers that make up an application into logical units for easy management and discovery.",
            "structured_data": {"language": "yaml", "type": "infrastructure", "topics": ["containers", "orchestration", "devops", "cloud"]},
            "domain": "kubernetes.io",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://openai.com/api/",
            "title": "OpenAI API Documentation",
            "description": "Build AI-powered applications using GPT-4, DALL-E, and other models.",
            "content": "The OpenAI API can be applied to virtually any task that requires understanding or generating natural language and code. We offer a range of models with different capabilities and price points, as well as the ability to fine-tune custom models.",
            "structured_data": {"language": "python", "type": "api", "topics": ["ai", "llm", "gpt", "machine-learning"]},
            "domain": "openai.com",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://stripe.com/docs/api",
            "title": "Stripe API Reference",
            "description": "Complete reference documentation for the Stripe API.",
            "content": "The Stripe API is organized around REST. Our API has predictable resource-oriented URLs, accepts form-encoded request bodies, returns JSON-encoded responses, and uses standard HTTP response codes, authentication, and verbs.",
            "structured_data": {"language": "curl", "type": "api", "topics": ["payments", "fintech", "rest", "webhooks"]},
            "domain": "stripe.com",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://tailwindcss.com/docs",
            "title": "Tailwind CSS Documentation",
            "description": "A utility-first CSS framework for rapidly building custom designs.",
            "content": "Tailwind CSS is a utility-first CSS framework packed with classes like flex, pt-4, text-center and rotate-90 that can be composed to build any design, directly in your markup. It's fast, flexible, and reliable with zero-runtime.",
            "structured_data": {"language": "css", "type": "framework", "topics": ["css", "frontend", "styling", "utility"]},
            "domain": "tailwindcss.com",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    await db.crawled_content.delete_many({})
    await db.crawled_content.insert_many(sample_content)
    
    try:
        await db.crawled_content.create_index([("title", "text"), ("content", "text"), ("description", "text")])
    except:
        pass
    
    return {"message": f"Seeded {len(sample_content)} sample content items"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Start webhook processor and scheduled crawl runner on startup
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_webhook_queue())
    logger.info("Webhook processor started")
    
    # Ensure text search index exists
    try:
        await db.crawled_content.create_index([("title", "text"), ("content", "text"), ("description", "text")])
    except:
        pass
    
    # Start scheduled crawl runner
    asyncio.create_task(run_scheduled_crawls())
    logger.info("Scheduled crawl runner started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
