from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from datetime import datetime, timezone
import uuid
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from app.database import db, client
from app.crawler import process_webhook_queue

# Import all routers
from app.routers.auth import router as auth_router
from app.routers.keys import router as keys_router
from app.routers.agents import router as agents_router
from app.routers.webhooks import router as webhooks_router
from app.routers.search import router as search_router
from app.routers.crawl import router as crawl_router, run_scheduled_crawls
from app.routers.sources import router as sources_router
from app.routers.analytics import router as analytics_router
from app.routers.rules import router as rules_router
from app.routers.ranking import router as ranking_router
from app.routers.orgs import router as orgs_router
from app.routers.billing import router as billing_router

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


# ==================== Misc Routes (kept in server.py) ====================

@api_router.get("/")
async def root():
    return {
        "name": "Remora API",
        "version": "1.0.0",
        "description": "API-first search engine for AI agents",
        "docs": "/docs",
        "endpoints": {
            "search": {
                "method": "POST",
                "path": "/api/search",
                "description": "Search indexed content using natural language queries",
                "auth": "API Key (X-API-Key header)",
                "request": {
                    "query": "string (required)",
                    "intent": "string (optional)",
                    "filters": "object (optional)",
                    "max_results": "integer (default: 10)",
                    "boost_domains": "array[string] (optional)",
                    "prefer_types": "array[string] (optional)",
                    "recency_boost": "boolean (default: true)",
                    "sort_by": "string (optional) - relevance or recency",
                    "ranking_config_id": "string (optional)"
                },
                "example_request": {
                    "query": "python async patterns",
                    "max_results": 5,
                    "boost_domains": ["docs.python.org"],
                    "recency_boost": True
                },
                "example_response": {
                    "results": [
                        {
                            "content_id": "content_abc123",
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
                "auth": "API Key"
            },
            "crawl": {
                "method": "POST",
                "path": "/api/crawl",
                "description": "Crawl a single URL and extract structured data",
                "auth": "Session (Dashboard)"
            },
            "bulk_crawl": {
                "method": "POST",
                "path": "/api/crawl/bulk",
                "description": "Submit multiple URLs for background crawling",
                "auth": "Session (Dashboard)"
            },
            "agents": {
                "method": "POST",
                "path": "/api/agents",
                "description": "Register a new agent",
                "auth": "Session (Dashboard)"
            },
            "webhooks": {
                "method": "POST",
                "path": "/api/webhooks",
                "description": "Subscribe to event notifications",
                "auth": "Session (Dashboard)"
            },
            "api_keys": {
                "method": "POST",
                "path": "/api/keys",
                "description": "Create a new API key",
                "auth": "Session (Dashboard)"
            }
        },
        "code_examples": {
            "python": 'import requests\n\nAPI_KEY = "rmr_your_api_key"\nBASE_URL = "https://your-app.com/api"\n\nresponse = requests.post(\n    f"{BASE_URL}/search",\n    headers={"X-API-Key": API_KEY},\n    json={"query": "python async", "max_results": 5}\n)\nresults = response.json()\nprint(f"Found {results[\'total\']} results")\n',
            "curl": 'curl -X POST "https://your-app.com/api/search" \\\n    -H "X-API-Key: rmr_your_api_key" \\\n    -H "Content-Type: application/json" \\\n    -d \'{"query": "python async", "max_results": 5}\'\n'
        }
    }


@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "search": "mongodb_text_search",
        "webhook_queue": "mongodb",
    }


@api_router.post("/seed")
async def seed_sample_data():
    sample_content = [
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://docs.python.org/3/library/asyncio.html",
            "title": "asyncio - Asynchronous I/O",
            "description": "asyncio is a library to write concurrent code using async/await syntax.",
            "content": "asyncio is a library to write concurrent code using the async/await syntax. It is used as a foundation for multiple Python asynchronous frameworks.",
            "structured_data": {"language": "python", "type": "documentation", "topics": ["async", "concurrency"]},
            "domain": "docs.python.org",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://react.dev/learn",
            "title": "React Documentation - Quick Start",
            "description": "Learn React with official documentation and examples.",
            "content": "React lets you build user interfaces out of individual pieces called components.",
            "structured_data": {"language": "javascript", "type": "documentation", "topics": ["react", "frontend"]},
            "domain": "react.dev",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://fastapi.tiangolo.com/",
            "title": "FastAPI - Modern Python Web Framework",
            "description": "FastAPI framework, high performance, easy to learn, fast to code.",
            "content": "FastAPI is a modern, fast web framework for building APIs with Python 3.7+ based on standard Python type hints.",
            "structured_data": {"language": "python", "type": "framework", "topics": ["api", "web", "backend"]},
            "domain": "fastapi.tiangolo.com",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://www.mongodb.com/docs/manual/",
            "title": "MongoDB Manual - NoSQL Database",
            "description": "MongoDB is a document database designed for ease of application development.",
            "content": "MongoDB stores data in flexible, JSON-like documents, meaning fields can vary from document to document.",
            "structured_data": {"language": "javascript", "type": "database", "topics": ["nosql", "database"]},
            "domain": "mongodb.com",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
        {
            "content_id": f"content_{uuid.uuid4().hex[:12]}",
            "url": "https://kubernetes.io/docs/home/",
            "title": "Kubernetes Documentation",
            "description": "Kubernetes is an open-source system for automating deployment of containerized apps.",
            "content": "Kubernetes groups containers into logical units for easy management and discovery.",
            "structured_data": {"language": "yaml", "type": "infrastructure", "topics": ["containers", "devops"]},
            "domain": "kubernetes.io",
            "crawled_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat()
        },
    ]

    await db.crawled_content.delete_many({})
    await db.crawled_content.insert_many(sample_content)

    try:
        await db.crawled_content.create_index([("title", "text"), ("content", "text"), ("description", "text")])
    except:
        pass

    return {"message": f"Seeded {len(sample_content)} sample content items"}


# ==================== Register all routers ====================
# NOTE: Order matters for path-conflict resolution. Static paths before parameterized.
api_router.include_router(auth_router)
api_router.include_router(keys_router)
api_router.include_router(agents_router)
api_router.include_router(webhooks_router)
api_router.include_router(search_router)
api_router.include_router(crawl_router)
api_router.include_router(sources_router)
api_router.include_router(analytics_router)
api_router.include_router(rules_router)
api_router.include_router(ranking_router)
api_router.include_router(orgs_router)
api_router.include_router(billing_router)

# Include the api_router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(process_webhook_queue())
    logger.info("Webhook processor started")

    try:
        await db.crawled_content.create_index([("title", "text"), ("content", "text"), ("description", "text")])
    except:
        pass

    asyncio.create_task(run_scheduled_crawls())
    logger.info("Scheduled crawl runner started")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
