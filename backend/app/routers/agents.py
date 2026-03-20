from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime, timezone
import uuid

from app.database import db
from app.models import User, Agent, AgentCreate, AgentUpdate
from app.auth import get_current_user

router = APIRouter()


@router.get("/agents", response_model=List[Agent])
async def list_agents(user: User = Depends(get_current_user)):
    """List all agents for current user"""
    agents = await db.agents.find({"user_id": user.user_id}, {"_id": 0}).to_list(100)
    for agent in agents:
        if isinstance(agent.get("created_at"), str):
            agent["created_at"] = datetime.fromisoformat(agent["created_at"])
        if isinstance(agent.get("updated_at"), str):
            agent["updated_at"] = datetime.fromisoformat(agent["updated_at"])
    return agents


@router.post("/agents", response_model=Agent)
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


@router.put("/agents/{agent_id}", response_model=Agent)
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


@router.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str, user: User = Depends(get_current_user)):
    """Delete an agent"""
    result = await db.agents.delete_one({"agent_id": agent_id, "user_id": user.user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"message": "Agent deleted"}
