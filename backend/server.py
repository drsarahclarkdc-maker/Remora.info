from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import secrets
import hashlib
import aiohttp
import meilisearch
import redis
import json
import httpx
from bs4 import BeautifulSoup
import asyncio
from urllib.parse import urlparse

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Meilisearch connection
MEILI_HOST = os.environ.get('MEILI_HOST', 'http://127.0.0.1:7700')
MEILI_KEY = os.environ.get('MEILI_MASTER_KEY', 'remora_master_key_2026')

try:
    meili_client = meilisearch.Client(MEILI_HOST, MEILI_KEY)
    meili_client.health()
    MEILI_AVAILABLE = True
    # Create content index if not exists
    try:
        meili_client.create_index('content', {'primaryKey': 'content_id'})
    except:
        pass
    # Configure index settings
    content_index = meili_client.index('content')
    content_index.update_searchable_attributes(['title', 'description', 'content'])
    content_index.update_filterable_attributes(['type', 'language', 'domain'])
    content_index.update_sortable_attributes(['crawled_at'])
except Exception as e:
    MEILI_AVAILABLE = False
    meili_client = None
    print(f"Meilisearch not available: {e}")

# Redis connection for webhook queue
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

try:
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, decode_responses=True)
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception as e:
    REDIS_AVAILABLE = False
    redis_client = None
    print(f"Redis not available: {e}")

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

# ==================== Models ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserSession(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    session_token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class APIKey(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key_id: str
    user_id: str
    name: str
    key_hash: str
    prefix: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None

class APIKeyCreate(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    prefix: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None

class APIKeyCreatedResponse(BaseModel):
    key_id: str
    name: str
    api_key: str
    prefix: str
    created_at: datetime

class Agent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    agent_id: str
    user_id: str
    name: str
    description: Optional[str] = None
    capabilities: List[str] = []
    endpoint_url: Optional[str] = None
    auth_type: str = "api_key"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    capabilities: List[str] = []
    endpoint_url: Optional[str] = None
    auth_type: str = "api_key"

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    endpoint_url: Optional[str] = None
    auth_type: Optional[str] = None
    is_active: Optional[bool] = None

class Webhook(BaseModel):
    model_config = ConfigDict(extra="ignore")
    webhook_id: str
    user_id: str
    name: str
    url: str
    events: List[str] = []
    secret: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivery_count: int = 0
    last_delivery: Optional[datetime] = None

class WebhookCreate(BaseModel):
    name: str
    url: str
    events: List[str] = []

class WebhookUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    events: Optional[List[str]] = None
    is_active: Optional[bool] = None

class UsageRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    record_id: str
    key_id: str
    user_id: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SearchQuery(BaseModel):
    query: str
    intent: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    max_results: int = 10

class SearchResult(BaseModel):
    results: List[Dict[str, Any]]
    total: int
    query: str
    processing_time_ms: int

class CrawledContent(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content_id: str
    url: str
    title: str
    description: Optional[str] = None
    content: str
    structured_data: Dict[str, Any] = {}
    domain: str
    crawled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CrawlRequest(BaseModel):
    url: str
    extract_links: bool = False

class BulkCrawlRequest(BaseModel):
    urls: List[str]
    
class BulkCrawlResponse(BaseModel):
    job_id: str
    total_urls: int
    status: str
    message: str

class CrawlJob(BaseModel):
    model_config = ConfigDict(extra="ignore")
    job_id: str
    user_id: str
    urls: List[str]
    status: str = "pending"  # pending, processing, completed, failed
    completed: int = 0
    failed: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class ScheduledCrawl(BaseModel):
    model_config = ConfigDict(extra="ignore")
    schedule_id: str
    user_id: str
    url: str
    frequency: str = "daily"  # hourly, daily, weekly
    is_active: bool = True
    last_crawl: Optional[datetime] = None
    next_crawl: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ScheduledCrawlCreate(BaseModel):
    url: str
    frequency: str = "daily"

class WebhookDelivery(BaseModel):
    delivery_id: str
    webhook_id: str
    event: str
    payload: Dict[str, Any]
    status: str = "pending"
    attempts: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    delivered_at: Optional[datetime] = None

# ==================== Auth Helpers ====================

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
    """Record API usage - free for now, just tracking"""
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

# ==================== Webhook Queue Helpers ====================

async def queue_webhook_delivery(event: str, payload: Dict[str, Any], user_id: str):
    """Queue webhook deliveries for all matching subscriptions"""
    if not REDIS_AVAILABLE:
        logger.warning("Redis not available, webhook delivery skipped")
        return
    
    webhooks = await db.webhooks.find(
        {"user_id": user_id, "is_active": True, "events": event},
        {"_id": 0}
    ).to_list(100)
    
    for webhook in webhooks:
        delivery = {
            "delivery_id": f"del_{uuid.uuid4().hex[:12]}",
            "webhook_id": webhook["webhook_id"],
            "url": webhook["url"],
            "secret": webhook["secret"],
            "event": event,
            "payload": payload,
            "attempts": 0,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        redis_client.lpush("webhook_queue", json.dumps(delivery))
    
    logger.info(f"Queued {len(webhooks)} webhook deliveries for event: {event}")

async def process_webhook_queue():
    """Process webhook delivery queue (background task)"""
    if not REDIS_AVAILABLE:
        return
    
    while True:
        try:
            item = redis_client.rpop("webhook_queue")
            if not item:
                await asyncio.sleep(1)
                continue
            
            delivery = json.loads(item)
            
            # Sign the payload
            signature = hashlib.sha256(
                (delivery["secret"] + json.dumps(delivery["payload"])).encode()
            ).hexdigest()
            
            headers = {
                "Content-Type": "application/json",
                "X-Remora-Event": delivery["event"],
                "X-Remora-Signature": signature,
                "X-Remora-Delivery": delivery["delivery_id"]
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    delivery["url"],
                    json=delivery["payload"],
                    headers=headers
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    # Success - update webhook stats
                    await db.webhooks.update_one(
                        {"webhook_id": delivery["webhook_id"]},
                        {
                            "$inc": {"delivery_count": 1},
                            "$set": {"last_delivery": datetime.now(timezone.utc).isoformat()}
                        }
                    )
                    logger.info(f"Webhook delivered: {delivery['delivery_id']}")
                else:
                    # Failed - retry if attempts < 3
                    delivery["attempts"] += 1
                    if delivery["attempts"] < 3:
                        redis_client.lpush("webhook_queue", json.dumps(delivery))
                        logger.warning(f"Webhook delivery failed, retrying: {delivery['delivery_id']}")
                    else:
                        logger.error(f"Webhook delivery failed permanently: {delivery['delivery_id']}")
                        
        except Exception as e:
            logger.error(f"Webhook processing error: {e}")
            await asyncio.sleep(1)

# ==================== Web Crawler ====================

async def crawl_url(url: str) -> Dict[str, Any]:
    """Crawl a URL and extract structured data"""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers={
                "User-Agent": "Remora/1.0 (AI Agent Search Engine; https://remora.info)"
            })
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Extract title
            title = ""
            if soup.title:
                title = soup.title.string or ""
            elif soup.find('h1'):
                title = soup.find('h1').get_text(strip=True)
            
            # Extract description
            description = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')
            elif soup.find('meta', attrs={'property': 'og:description'}):
                description = soup.find('meta', attrs={'property': 'og:description'}).get('content', '')
            
            # Extract main content
            content = ""
            # Try common content containers
            for selector in ['article', 'main', '.content', '#content', '.post-content', '.entry-content']:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(separator=' ', strip=True)
                    break
            
            if not content:
                # Fallback to body text
                for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'header']):
                    tag.decompose()
                content = soup.get_text(separator=' ', strip=True)
            
            # Limit content length
            content = content[:10000] if len(content) > 10000 else content
            
            # Extract structured data (JSON-LD, microdata, etc.)
            structured_data = {}
            
            # JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    ld_data = json.loads(script.string)
                    if isinstance(ld_data, dict):
                        structured_data['json_ld'] = ld_data
                except:
                    pass
            
            # Open Graph
            og_data = {}
            for meta in soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')}):
                key = meta.get('property', '').replace('og:', '')
                og_data[key] = meta.get('content', '')
            if og_data:
                structured_data['open_graph'] = og_data
            
            # Detect type and language
            lang = soup.html.get('lang', 'en') if soup.html else 'en'
            doc_type = 'webpage'
            if soup.find('code') or soup.find('pre'):
                doc_type = 'documentation'
            elif soup.find('article'):
                doc_type = 'article'
            
            structured_data['type'] = doc_type
            structured_data['language'] = lang[:2]
            
            # Extract domain
            parsed = urlparse(url)
            domain = parsed.netloc
            
            return {
                "url": url,
                "title": title.strip()[:500],
                "description": description.strip()[:1000],
                "content": content,
                "structured_data": structured_data,
                "domain": domain
            }
            
    except Exception as e:
        logger.error(f"Crawl error for {url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to crawl URL: {str(e)}")

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
    FREE for everyone - just tracking usage.
    """
    import time
    start_time = time.time()
    
    user = await get_user_from_api_key(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    api_key = request.headers.get("X-API-Key")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_doc = await db.api_keys.find_one({"key_hash": key_hash}, {"_id": 0})
    
    results = []
    total = 0
    
    # Use Meilisearch if available
    if MEILI_AVAILABLE and meili_client:
        try:
            index = meili_client.index("content")
            search_params = {"limit": query.max_results}
            
            if query.filters:
                filter_parts = []
                for key, value in query.filters.items():
                    filter_parts.append(f'{key} = "{value}"')
                if filter_parts:
                    search_params["filter"] = " AND ".join(filter_parts)
            
            meili_results = index.search(query.query, search_params)
            results = meili_results.get("hits", [])
            total = meili_results.get("estimatedTotalHits", 0)
        except Exception as e:
            logger.warning(f"Meilisearch error: {e}")
    
    # Fallback to MongoDB text search
    if not results:
        try:
            await db.crawled_content.create_index([("title", "text"), ("content", "text"), ("description", "text")])
            
            mongo_query = {"$text": {"$search": query.query}}
            if query.filters:
                mongo_query.update(query.filters)
            
            cursor = db.crawled_content.find(
                mongo_query,
                {"_id": 0, "score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(query.max_results)
            
            results = await cursor.to_list(query.max_results)
            total = len(results)
        except Exception as e:
            logger.warning(f"MongoDB search error: {e}")
            results = []
            total = 0
    
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
    """Get specific content by ID (API key auth for agents)"""
    user = await get_user_from_api_key(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    content = await db.crawled_content.find_one(
        {"content_id": content_id},
        {"_id": 0}
    )
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return content

@api_router.post("/crawl")
async def crawl_website(crawl_request: CrawlRequest, background_tasks: BackgroundTasks, user: User = Depends(get_current_user)):
    """Crawl a URL and extract structured data"""
    data = await crawl_url(crawl_request.url)
    
    content_id = f"content_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
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
    
    # Index in Meilisearch
    if MEILI_AVAILABLE and meili_client:
        try:
            index = meili_client.index("content")
            index.add_documents([doc])
        except Exception as e:
            logger.warning(f"Failed to index in Meilisearch: {e}")
    
    # Queue webhook notification
    background_tasks.add_task(
        queue_webhook_delivery,
        "content.new",
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
            
            if MEILI_AVAILABLE and meili_client:
                try:
                    meili_client.index("content").add_documents([doc])
                except:
                    pass
            
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
    """
    Submit multiple URLs for crawling in the background.
    Returns a job ID to track progress.
    """
    if len(request.urls) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 URLs per request")
    
    if len(request.urls) == 0:
        raise HTTPException(status_code=400, detail="At least one URL required")
    
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
        
        if MEILI_AVAILABLE and meili_client:
            meili_client.index("content").add_documents([content_doc])
        
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
                    
                    if MEILI_AVAILABLE and meili_client:
                        meili_client.index("content").add_documents([content_doc])
                    
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
        "meilisearch": "connected" if MEILI_AVAILABLE else "unavailable",
        "redis": "connected" if REDIS_AVAILABLE else "unavailable",
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
    
    # Index in Meilisearch
    if MEILI_AVAILABLE and meili_client:
        try:
            index = meili_client.index("content")
            index.add_documents(sample_content)
        except Exception as e:
            logger.warning(f"Failed to index in Meilisearch: {e}")
    
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
    if REDIS_AVAILABLE:
        asyncio.create_task(process_webhook_queue())
        logger.info("Webhook processor started")
    
    # Start scheduled crawl runner
    asyncio.create_task(run_scheduled_crawls())
    logger.info("Scheduled crawl runner started")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
