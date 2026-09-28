from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, Dict
import time
import uuid

router = APIRouter(prefix="/v1/family", tags=["family"])

# In-memory storage for prototype
# Key: code, Value: record dict
INVITES_DB: Dict[str, dict] = {}
# Key: token, Value: session dict
SESSIONS_DB: Dict[str, dict] = {}

class InviteRequest(BaseModel):
    role: str # 'partner', 'parent', 'sibling'
    expiry_hours: int = 24

class InviteResponse(BaseModel):
    invite_code: str
    role: str
    expires_at: int

class AcceptRequest(BaseModel):
    invite_code: str

class AcceptResponse(BaseModel):
    session_token: str
    role: str

class SharedFamilyView(BaseModel):
    role: str
    current_phase: str # 'follicular', 'ovulatory', 'luteal', 'menstrual'
    expected_window_coarse: Optional[str] = None # 3-day window, absent for sibling
    support_tip: str
    # CRITICAL PRIVACY GUARANTEE: NO raw cycle_length, flow_intensity, pain_score, or symptoms fields!

class RevokeRequest(BaseModel):
    invite_code: str

@router.post("/invite", response_model=InviteResponse)
def create_family_invite(req: InviteRequest):
    if req.role not in ["partner", "parent", "sibling"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be partner, parent, or sibling.")
    
    code = f"MC-{uuid.uuid4().hex[:6].upper()}"
    expires_at = int(time.time()) + (req.expiry_hours * 3600)
    
    record = {
        "invite_code": code,
        "role": req.role,
        "expires_at": expires_at,
        "revoked": False,
        "coarse_phase": "follicular",
        "expected_window_coarse": "Jul 24 - Jul 26" if req.role in ["partner", "parent"] else None,
    }
    INVITES_DB[code] = record
    return InviteResponse(invite_code=code, role=req.role, expires_at=expires_at)

@router.post("/accept", response_model=AcceptResponse)
def accept_family_invite(req: AcceptRequest):
    record = INVITES_DB.get(req.invite_code)
    if not record:
        raise HTTPException(status_code=440, detail="Invite code not found.")
    if record["revoked"]:
        raise HTTPException(status_code=403, detail="Invite code has been revoked.")
    if time.time() > record["expires_at"]:
        raise HTTPException(status_code=410, detail="Invite code has expired.")
    
    token = f"sess_{uuid.uuid4().hex}"
    SESSIONS_DB[token] = {
        "invite_code": req.invite_code,
        "role": record["role"],
    }
    return AcceptResponse(session_token=token, role=record["role"])

@router.get("/view", response_model=SharedFamilyView)
def get_family_view(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    
    token = authorization.split(" ")[1]
    session = SESSIONS_DB.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token.")
    
    invite_record = INVITES_DB.get(session["invite_code"])
    if not invite_record or invite_record["revoked"]:
        raise HTTPException(status_code=403, detail="Access revoked by user.")
    
    role = session["role"]
    coarse_phase = invite_record["coarse_phase"]
    
    tip_text = (
        "Supportive environment and steady hydration recommended."
        if role != "parent"
        else "Ensure iron-rich food options (spinach, lentils, jaggery) and warm drinks."
    )

    return SharedFamilyView(
        role=role,
        current_phase=coarse_phase,
        expected_window_coarse=invite_record["expected_window_coarse"] if role in ["partner", "parent"] else None,
        support_tip=tip_text,
    )

@router.post("/revoke")
def revoke_family_invite(req: RevokeRequest):
    record = INVITES_DB.get(req.invite_code)
    if not record:
        raise HTTPException(status_code=404, detail="Code not found.")
    record["revoked"] = True
    return {"status": "success", "message": f"Invite code {req.invite_code} successfully revoked."}
