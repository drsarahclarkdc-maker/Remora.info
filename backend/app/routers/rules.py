from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
import uuid

from app.database import db
from app.models import User, CrawlRule, CrawlRuleCreate, CrawlRuleUpdate
from app.auth import get_current_user

router = APIRouter()


@router.get("/rules")
async def list_crawl_rules(user: User = Depends(get_current_user)):
    return await db.crawl_rules.find({"user_id": user.user_id}, {"_id": 0}).to_list(100)


@router.post("/rules")
async def create_crawl_rule(rule_data: CrawlRuleCreate, user: User = Depends(get_current_user)):
    rule = CrawlRule(rule_id=f"rule_{uuid.uuid4().hex[:12]}", user_id=user.user_id, **rule_data.model_dump())
    doc = rule.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["updated_at"] = doc["updated_at"].isoformat()
    await db.crawl_rules.insert_one(doc)
    return doc


@router.get("/rules/{rule_id}")
async def get_crawl_rule(rule_id: str, user: User = Depends(get_current_user)):
    rule = await db.crawl_rules.find_one({"rule_id": rule_id, "user_id": user.user_id}, {"_id": 0})
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return rule


@router.put("/rules/{rule_id}")
async def update_crawl_rule(rule_id: str, rule_data: CrawlRuleUpdate, user: User = Depends(get_current_user)):
    update_data = {k: v for k, v in rule_data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.crawl_rules.update_one({"rule_id": rule_id, "user_id": user.user_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return await db.crawl_rules.find_one({"rule_id": rule_id}, {"_id": 0})


@router.delete("/rules/{rule_id}")
async def delete_crawl_rule(rule_id: str, user: User = Depends(get_current_user)):
    result = await db.crawl_rules.delete_one({"rule_id": rule_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted"}


@router.get("/rules/domain/{domain}")
async def get_rules_for_domain(domain: str, user: User = Depends(get_current_user)):
    rules = await db.crawl_rules.find({"user_id": user.user_id, "domain": domain, "is_active": True}, {"_id": 0}).to_list(10)
    return rules
