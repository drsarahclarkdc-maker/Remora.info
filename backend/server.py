from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Meilisearch connection (using local instance or mock if not available)
MEILI_HOST = os.environ.get('MEILI_HOST', 'http://localhost:7700')
MEILI_KEY = os.environ.get('MEILI_MASTER_KEY', 'masterKey')

try:
    meili_client = meilisearch.Client(MEILI_HOST, MEILI_KEY)
    meili_client.health()
    MEILI_AVAILABLE = True
except:
    MEILI_AVAILABLE = False
    meili_client = None

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

# Rate Limiting Tiers
RATE_LIMITS = {
    "free": 100,      # 100 requests/day
    "pro": 10000,     # 10K requests/day
    "enterprise": -1  # Unlimited (-1)
}

# ==================== Models ====================

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    tier: str = "free"
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
    prefix: str  # First 8 chars for display
    tier: str = "free"
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_used: Optional[datetime] = None

class APIKeyCreate(BaseModel):
    name: str

class APIKeyResponse(BaseModel):
    key_id: str
    name: str
    prefix: str
    tier: str
    is_active: bool
    created_at: datetime
    last_used: Optional[datetime] = None

class APIKeyCreatedResponse(BaseModel):
    key_id: str
    name: str
    api_key: str  # Only returned on creation
    prefix: str
    tier: str
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
    crawled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== Auth Helpers ====================

async def get_current_user(request: Request) -> User:
    """Get current user from session token (cookie or header)"""
    # Try cookie first
    session_token = request.cookies.get("session_token")
    
    # Fallback to Authorization header
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header.split(" ")[1]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Find session
    session_doc = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session_doc:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session_doc["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user_doc = await db.users.find_one(
        {"user_id": session_doc["user_id"]},
        {"_id": 0}
    )
    
    if not user_doc:
        raise HTTPException(status_code=401, detail="User not found")
    
    # Parse datetime
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
    
    # Update last used
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

async def check_rate_limit(user: User, key_id: str) -> bool:
    """Check if user is within rate limit"""
    tier = user.tier
    limit = RATE_LIMITS.get(tier, 100)
    
    if limit == -1:  # Unlimited
        return True
    
    # Count today's requests
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    count = await db.usage_records.count_documents({
        "key_id": key_id,
        "timestamp": {"$gte": today_start.isoformat()}
    })
    
    return count < limit

async def record_usage(key_id: str, user_id: str, endpoint: str, method: str, status_code: int, response_time_ms: int):
    """Record API usage"""
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
    
    # Get user data from Emergent Auth
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
    
    # Check if user exists
    existing_user = await db.users.find_one(
        {"email": auth_data["email"]},
        {"_id": 0}
    )
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": auth_data.get("name", existing_user.get("name")),
                "picture": auth_data.get("picture", existing_user.get("picture"))
            }}
        )
    else:
        # Create new user
        user = User(
            user_id=user_id,
            email=auth_data["email"],
            name=auth_data.get("name", "User"),
            picture=auth_data.get("picture"),
            tier="free"
        )
        doc = user.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.users.insert_one(doc)
    
    # Create session
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at
    )
    session_doc = session.model_dump()
    session_doc["expires_at"] = session_doc["expires_at"].isoformat()
    session_doc["created_at"] = session_doc["created_at"].isoformat()
    
    # Delete old sessions for user
    await db.user_sessions.delete_many({"user_id": user_id})
    await db.user_sessions.insert_one(session_doc)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=7 * 24 * 60 * 60  # 7 days
    )
    
    # Get user for response
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
    # Generate API key
    api_key = f"rmr_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    prefix = api_key[:12]
    
    key = APIKey(
        key_id=f"key_{uuid.uuid4().hex[:12]}",
        user_id=user.user_id,
        name=key_data.name,
        key_hash=key_hash,
        prefix=prefix,
        tier=user.tier
    )
    
    doc = key.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.api_keys.insert_one(doc)
    
    return APIKeyCreatedResponse(
        key_id=key.key_id,
        name=key.name,
        api_key=api_key,  # Only returned once!
        prefix=prefix,
        tier=key.tier,
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

@api_router.get("/webhooks", response_model=List[Webhook])
async def list_webhooks(user: User = Depends(get_current_user)):
    """List all webhooks for current user"""
    webhooks = await db.webhooks.find(
        {"user_id": user.user_id},
        {"_id": 0, "secret": 0}  # Hide secret in list
    ).to_list(100)
    
    for webhook in webhooks:
        webhook["secret"] = "***"  # Masked
        if isinstance(webhook.get("created_at"), str):
            webhook["created_at"] = datetime.fromisoformat(webhook["created_at"])
    
    return webhooks

@api_router.post("/webhooks", response_model=Webhook)
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
    
    return webhook

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
    
    webhook_doc = await db.webhooks.find_one({"webhook_id": webhook_id}, {"_id": 0})
    if isinstance(webhook_doc.get("created_at"), str):
        webhook_doc["created_at"] = datetime.fromisoformat(webhook_doc["created_at"])
    
    return Webhook(**webhook_doc)

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

# ==================== Search API (Agent Query API) ====================

@api_router.post("/search", response_model=SearchResult)
async def agent_search(query: SearchQuery, request: Request):
    """
    Agent Query API - accepts structured JSON queries, returns JSON results.
    Requires API key authentication via X-API-Key header.
    """
    import time
    start_time = time.time()
    
    # Get user from API key
    user = await get_user_from_api_key(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    
    # Get API key for rate limiting
    api_key = request.headers.get("X-API-Key")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_doc = await db.api_keys.find_one({"key_hash": key_hash}, {"_id": 0})
    
    # Check rate limit
    if not await check_rate_limit(user, key_doc["key_id"]):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    results = []
    total = 0
    
    # Try Meilisearch if available
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
            # Ensure text index exists
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
    
    # Record usage
    await record_usage(
        key_id=key_doc["key_id"],
        user_id=user.user_id,
        endpoint="/api/search",
        method="POST",
        status_code=200,
        response_time_ms=processing_time
    )
    
    return SearchResult(
        results=results,
        total=total,
        query=query.query,
        processing_time_ms=processing_time
    )

# ==================== Usage & Analytics Routes ====================

@api_router.get("/usage/stats")
async def get_usage_stats(user: User = Depends(get_current_user)):
    """Get usage statistics for current user"""
    # Today's stats
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    today_count = await db.usage_records.count_documents({
        "user_id": user.user_id,
        "timestamp": {"$gte": today_start.isoformat()}
    })
    
    # This week's stats
    week_start = today_start - timedelta(days=today_start.weekday())
    week_count = await db.usage_records.count_documents({
        "user_id": user.user_id,
        "timestamp": {"$gte": week_start.isoformat()}
    })
    
    # This month's stats
    month_start = today_start.replace(day=1)
    month_count = await db.usage_records.count_documents({
        "user_id": user.user_id,
        "timestamp": {"$gte": month_start.isoformat()}
    })
    
    # Total stats
    total_count = await db.usage_records.count_documents({"user_id": user.user_id})
    
    # Get daily breakdown for last 7 days
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
    
    # Average response time
    pipeline = [
        {"$match": {"user_id": user.user_id}},
        {"$group": {"_id": None, "avg_response_time": {"$avg": "$response_time_ms"}}}
    ]
    avg_result = await db.usage_records.aggregate(pipeline).to_list(1)
    avg_response_time = avg_result[0]["avg_response_time"] if avg_result else 0
    
    # Rate limit info
    limit = RATE_LIMITS.get(user.tier, 100)
    remaining = max(0, limit - today_count) if limit > 0 else -1
    
    return {
        "today": today_count,
        "this_week": week_count,
        "this_month": month_count,
        "total": total_count,
        "daily_breakdown": list(reversed(daily_stats)),
        "avg_response_time_ms": round(avg_response_time, 2),
        "rate_limit": {
            "tier": user.tier,
            "limit": limit,
            "used_today": today_count,
            "remaining": remaining
        }
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

# ==================== Content Management (Translation Layer) ====================

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
    
    if isinstance(content.get("crawled_at"), str):
        content["crawled_at"] = datetime.fromisoformat(content["crawled_at"])
    if isinstance(content.get("last_updated"), str):
        content["last_updated"] = datetime.fromisoformat(content["last_updated"])
    
    return content

# ==================== Health & Status ====================

@api_router.get("/")
async def root():
    return {"message": "Remora API - Search Engine for AI Agents", "version": "1.0.0"}

@api_router.get("/health")
async def health_check():
    """Health check endpoint"""
    health = {
        "status": "healthy",
        "database": "connected",
        "meilisearch": "connected" if MEILI_AVAILABLE else "unavailable"
    }
    return health

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
            "structured_data": {
                "language": "python",
                "type": "documentation",
                "topics": ["async", "concurrency", "networking"]
            },
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://react.dev/learn",
            "title": "React Documentation - Quick Start",
            "description": "Learn React with official documentation and examples.",
            "content": "React lets you build user interfaces out of individual pieces called components. Create your own React components like Thumbnail, LikeButton, and Video. Then combine them into entire screens, pages, and apps.",
            "structured_data": {
                "language": "javascript",
                "type": "documentation",
                "topics": ["react", "frontend", "components", "ui"]
            },
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://fastapi.tiangolo.com/",
            "title": "FastAPI - Modern Python Web Framework",
            "description": "FastAPI framework, high performance, easy to learn, fast to code, ready for production.",
            "content": "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints. Very high performance, on par with NodeJS and Go. Fast to code, fewer bugs, intuitive, easy, short, robust, standards-based.",
            "structured_data": {
                "language": "python",
                "type": "framework",
                "topics": ["api", "web", "backend", "rest"]
            },
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://www.mongodb.com/docs/manual/",
            "title": "MongoDB Manual - NoSQL Database",
            "description": "MongoDB is a document database designed for ease of application development and scaling.",
            "content": "MongoDB is a document database with the scalability and flexibility that you want with the querying and indexing that you need. MongoDB stores data in flexible, JSON-like documents, meaning fields can vary from document to document.",
            "structured_data": {
                "language": "javascript",
                "type": "database",
                "topics": ["nosql", "database", "documents", "json"]
            },
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://kubernetes.io/docs/home/",
            "title": "Kubernetes Documentation",
            "description": "Kubernetes is an open-source system for automating deployment, scaling, and management of containerized applications.",
            "content": "Kubernetes, also known as K8s, is an open-source system for automating deployment, scaling, and management of containerized applications. It groups containers that make up an application into logical units for easy management and discovery.",
            "structured_data": {
                "language": "yaml",
                "type": "infrastructure",
                "topics": ["containers", "orchestration", "devops", "cloud"]
            },
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://openai.com/api/",
            "title": "OpenAI API Documentation",
            "description": "Build AI-powered applications using GPT-4, DALL-E, and other models.",
            "content": "The OpenAI API can be applied to virtually any task that requires understanding or generating natural language and code. We offer a range of models with different capabilities and price points, as well as the ability to fine-tune custom models.",
            "structured_data": {
                "language": "python",
                "type": "api",
                "topics": ["ai", "llm", "gpt", "machine-learning"]
            },
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://stripe.com/docs/api",
            "title": "Stripe API Reference",
            "description": "Complete reference documentation for the Stripe API.",
            "content": "The Stripe API is organized around REST. Our API has predictable resource-oriented URLs, accepts form-encoded request bodies, returns JSON-encoded responses, and uses standard HTTP response codes, authentication, and verbs.",
            "structured_data": {
                "language": "curl",
                "type": "api",
                "topics": ["payments", "fintech", "rest", "webhooks"]
            },
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://tailwindcss.com/docs",
            "title": "Tailwind CSS Documentation",
            "description": "A utility-first CSS framework for rapidly building custom designs.",
            "content": "Tailwind CSS is a utility-first CSS framework packed with classes like flex, pt-4, text-center and rotate-90 that can be composed to build any design, directly in your markup. It's fast, flexible, and reliable with zero-runtime.",
            "structured_data": {
                "language": "css",
                "type": "framework",
                "topics": ["css", "frontend", "styling", "utility"]
            },
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    # Clear existing content
    await db.crawled_content.delete_many({})
    
    # Insert sample content
    await db.crawled_content.insert_many(sample_content)
    
    # Create text index for searching
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
