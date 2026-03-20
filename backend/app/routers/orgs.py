from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
import uuid
import re
import secrets

from app.database import db
from app.models import (
    User, Organization, OrganizationCreate,
    OrganizationMember, OrganizationInvite, InviteMemberRequest,
)
from app.auth import get_current_user

router = APIRouter()


def generate_slug(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug[:50]


@router.get("/orgs")
async def list_organizations(user: User = Depends(get_current_user)):
    memberships = await db.org_members.find(
        {"user_id": user.user_id}, {"_id": 0}
    ).to_list(50)
    org_ids = [m["org_id"] for m in memberships]
    orgs = await db.organizations.find(
        {"org_id": {"$in": org_ids}}, {"_id": 0}
    ).to_list(50)
    role_map = {m["org_id"]: m["role"] for m in memberships}
    for org in orgs:
        org["role"] = role_map.get(org["org_id"], "member")
    return orgs


@router.post("/orgs")
async def create_organization(org_data: OrganizationCreate, user: User = Depends(get_current_user)):
    slug = generate_slug(org_data.name)
    existing = await db.organizations.find_one({"slug": slug})
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    org = Organization(
        org_id=f"org_{uuid.uuid4().hex[:12]}",
        name=org_data.name, slug=slug, owner_id=user.user_id
    )
    doc = org.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.organizations.insert_one(doc)
    member = OrganizationMember(
        member_id=f"mem_{uuid.uuid4().hex[:12]}",
        org_id=org.org_id, user_id=user.user_id, role="owner"
    )
    member_doc = member.model_dump()
    member_doc["joined_at"] = member_doc["joined_at"].isoformat()
    await db.org_members.insert_one(member_doc)
    result = org.model_dump()
    result["role"] = "owner"
    return result


# Static routes MUST be before /orgs/{org_id} to avoid path conflicts
@router.get("/orgs/invites/pending")
async def list_pending_invites(user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    if not user_doc:
        return []
    invites = await db.org_invites.find({
        "email": user_doc["email"],
        "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
    }, {"_id": 0, "token": 0}).to_list(20)
    for invite in invites:
        org = await db.organizations.find_one({"org_id": invite["org_id"]}, {"_id": 0})
        if org:
            invite["org_name"] = org["name"]
    return invites


@router.post("/orgs/invites/{invite_id}/accept")
async def accept_invite(invite_id: str, user: User = Depends(get_current_user)):
    user_doc = await db.users.find_one({"user_id": user.user_id}, {"_id": 0})
    invite = await db.org_invites.find_one({
        "invite_id": invite_id, "email": user_doc["email"]
    })
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if datetime.fromisoformat(invite["expires_at"]) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite has expired")
    member = OrganizationMember(
        member_id=f"mem_{uuid.uuid4().hex[:12]}",
        org_id=invite["org_id"], user_id=user.user_id, role=invite["role"]
    )
    member_doc = member.model_dump()
    member_doc["joined_at"] = member_doc["joined_at"].isoformat()
    await db.org_members.insert_one(member_doc)
    await db.org_invites.delete_one({"invite_id": invite_id})
    return {"message": "Invite accepted", "org_id": invite["org_id"]}


@router.get("/orgs/{org_id}")
async def get_organization(org_id: str, user: User = Depends(get_current_user)):
    membership = await db.org_members.find_one({
        "org_id": org_id, "user_id": user.user_id
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    org["role"] = membership["role"]
    return org


@router.get("/orgs/{org_id}/members")
async def list_org_members(org_id: str, user: User = Depends(get_current_user)):
    membership = await db.org_members.find_one({
        "org_id": org_id, "user_id": user.user_id
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    members = await db.org_members.find({"org_id": org_id}, {"_id": 0}).to_list(100)
    for member in members:
        user_doc = await db.users.find_one({"user_id": member["user_id"]}, {"_id": 0})
        if user_doc:
            member["name"] = user_doc.get("name")
            member["email"] = user_doc.get("email")
            member["picture"] = user_doc.get("picture")
    return members


@router.post("/orgs/{org_id}/invite")
async def invite_member(org_id: str, invite_data: InviteMemberRequest, user: User = Depends(get_current_user)):
    membership = await db.org_members.find_one({
        "org_id": org_id, "user_id": user.user_id,
        "role": {"$in": ["owner", "admin"]}
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Only admins can invite members")
    existing_user = await db.users.find_one({"email": invite_data.email})
    if existing_user:
        existing_membership = await db.org_members.find_one({
            "org_id": org_id, "user_id": existing_user["user_id"]
        })
        if existing_membership:
            raise HTTPException(status_code=400, detail="User is already a member")
    invite = OrganizationInvite(
        invite_id=f"inv_{uuid.uuid4().hex[:12]}",
        org_id=org_id, email=invite_data.email, role=invite_data.role,
        invited_by=user.user_id, token=secrets.token_urlsafe(32),
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


@router.delete("/orgs/{org_id}/members/{member_user_id}")
async def remove_member(org_id: str, member_user_id: str, user: User = Depends(get_current_user)):
    membership = await db.org_members.find_one({
        "org_id": org_id, "user_id": user.user_id,
        "role": {"$in": ["owner", "admin"]}
    })
    if not membership:
        raise HTTPException(status_code=403, detail="Only admins can remove members")
    org = await db.organizations.find_one({"org_id": org_id})
    if org and org["owner_id"] == member_user_id:
        raise HTTPException(status_code=400, detail="Cannot remove organization owner")
    result = await db.org_members.delete_one({
        "org_id": org_id, "user_id": member_user_id
    })
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"message": "Member removed"}


@router.delete("/orgs/{org_id}")
async def delete_organization(org_id: str, user: User = Depends(get_current_user)):
    org = await db.organizations.find_one({"org_id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if org["owner_id"] != user.user_id:
        raise HTTPException(status_code=403, detail="Only owner can delete organization")
    await db.organizations.delete_one({"org_id": org_id})
    await db.org_members.delete_many({"org_id": org_id})
    await db.org_invites.delete_many({"org_id": org_id})
    return {"message": "Organization deleted"}
