from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Depends
from datetime import datetime, timezone
import hashlib
import time

from app.database import db
from app.models import User, SearchQuery, SearchResult, CREDIT_COSTS
from app.auth import get_user_from_api_key, record_usage, check_credits_or_block
from app.crawler import queue_webhook_delivery

router = APIRouter()


@router.post("/search", response_model=SearchResult)
async def agent_search(query: SearchQuery, request: Request, background_tasks: BackgroundTasks):
    """Agent Query API - accepts structured JSON queries, returns JSON results. Costs 1 credit."""
    start_time = time.time()

    user = await get_user_from_api_key(request)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    await check_credits_or_block(user.user_id, CREDIT_COSTS["search"], "search")

    api_key = request.headers.get("X-API-Key")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    key_doc = await db.api_keys.find_one({"key_hash": key_hash}, {"_id": 0})

    ranking_config = None
    if query.ranking_config_id:
        ranking_config = await db.ranking_configs.find_one(
            {"config_id": query.ranking_config_id, "user_id": user.user_id},
            {"_id": 0}
        )

    results = []
    total = 0

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
        results = []
        total = 0

    if results:
        now = datetime.now(timezone.utc)
        boost_domains = query.boost_domains or (ranking_config.get("boosted_domains", []) if ranking_config else [])
        penalize_domains = ranking_config.get("penalized_domains", []) if ranking_config else []
        prefer_types = query.prefer_types or (ranking_config.get("preferred_types", []) if ranking_config else [])
        domain_boost = ranking_config.get("domain_boost_factor", 1.5) if ranking_config else 1.5
        type_boost = ranking_config.get("type_boost_factor", 1.3) if ranking_config else 1.3
        recency_decay_days = ranking_config.get("recency_decay_days", 30) if ranking_config else 30
        apply_recency = query.recency_boost if query.recency_boost is not None else (ranking_config.get("recency_boost", True) if ranking_config else True)

        for result in results:
            score = result.get("score", 1.0) if isinstance(result.get("score"), (int, float)) else 1.0
            domain = result.get("domain", "")
            if domain in boost_domains:
                score *= domain_boost
            elif domain in penalize_domains:
                score *= 0.5
            content_type = result.get("structured_data", {}).get("type", "")
            if content_type in prefer_types:
                score *= type_boost
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
                        score *= (1 + recency_factor * 0.3)
            result["_ranking_score"] = score

        if query.sort_by == "recency":
            results.sort(key=lambda x: x.get("crawled_at", ""), reverse=True)
        else:
            results.sort(key=lambda x: x.get("_ranking_score", 0), reverse=True)

        results = results[:query.max_results]
        for result in results:
            result.pop("_ranking_score", None)
            result.pop("score", None)

    processing_time = int((time.time() - start_time) * 1000)

    await record_usage(
        key_id=key_doc["key_id"],
        user_id=user.user_id,
        endpoint="/api/search",
        method="POST",
        status_code=200,
        response_time_ms=processing_time
    )

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
