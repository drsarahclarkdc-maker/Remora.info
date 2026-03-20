from fastapi import APIRouter, HTTPException, Depends
import uuid

from app.database import db
from app.models import User, SearchRankingConfig, SearchRankingConfigCreate
from app.auth import get_current_user

router = APIRouter()


@router.get("/ranking")
async def list_ranking_configs(user: User = Depends(get_current_user)):
    return await db.ranking_configs.find({"user_id": user.user_id}, {"_id": 0}).to_list(50)


@router.post("/ranking")
async def create_ranking_config(config_data: SearchRankingConfigCreate, user: User = Depends(get_current_user)):
    if config_data.is_default:
        await db.ranking_configs.update_many({"user_id": user.user_id}, {"$set": {"is_default": False}})
    config = SearchRankingConfig(config_id=f"rank_{uuid.uuid4().hex[:12]}", user_id=user.user_id, **config_data.model_dump())
    doc = config.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.ranking_configs.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/ranking/{config_id}")
async def get_ranking_config(config_id: str, user: User = Depends(get_current_user)):
    config = await db.ranking_configs.find_one({"config_id": config_id, "user_id": user.user_id}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.put("/ranking/{config_id}")
async def update_ranking_config(config_id: str, config_data: SearchRankingConfigCreate, user: User = Depends(get_current_user)):
    existing = await db.ranking_configs.find_one({"config_id": config_id, "user_id": user.user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Config not found")
    if config_data.is_default:
        await db.ranking_configs.update_many({"user_id": user.user_id, "config_id": {"$ne": config_id}}, {"$set": {"is_default": False}})
    await db.ranking_configs.update_one({"config_id": config_id, "user_id": user.user_id}, {"$set": config_data.model_dump()})
    return await db.ranking_configs.find_one({"config_id": config_id}, {"_id": 0})


@router.delete("/ranking/{config_id}")
async def delete_ranking_config(config_id: str, user: User = Depends(get_current_user)):
    result = await db.ranking_configs.delete_one({"config_id": config_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"message": "Config deleted"}
