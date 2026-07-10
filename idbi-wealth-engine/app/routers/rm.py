from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.database import db, Lead

router = APIRouter(prefix="/rm", tags=["Relationship Manager"])

# Dependency to get db session
def get_db():
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()

# Pydantic models for request/response
class LeadUpdate(BaseModel):
    status: str  # 'pending', 'accepted', 'rejected', 'converted'
    rm_notes: Optional[str] = None
    assigned_rm: Optional[str] = None

class LeadResponse(BaseModel):
    id: int
    customer_id: str
    product_name: str
    product_type: str
    tier: str
    recommended_amount: int
    suitability_trail: list
    status: str
    priority_score: int
    assigned_rm: Optional[str]
    rm_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

@router.get("/leads", response_model=List[LeadResponse])
def get_leads(status: Optional[str] = None, session: Session = Depends(get_db)):
    """
    Get a list of prioritized leads, optionally filtered by status.
    """
    try:
        query = session.query(Lead)
        if status:
            query = query.filter(Lead.status == status)
        # Order by priority_score descending (HNI/Aggressive and higher amounts should be prioritized)
        leads = query.order_by(Lead.priority_score.desc(), Lead.created_at.desc()).all()
        return leads
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/leads/{lead_id}", response_model=LeadResponse)
def get_lead_details(lead_id: int, session: Session = Depends(get_db)):
    """
    Get detailed suitability audit trail and details for a specific lead.
    """
    lead = session.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.post("/leads/{lead_id}/action", response_model=LeadResponse)
def update_lead_status(lead_id: int, update: LeadUpdate, session: Session = Depends(get_db)):
    """
    Action a lead (accept, reject, convert) and add RM notes.
    """
    lead = session.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
        
    valid_statuses = ['pending', 'accepted', 'rejected', 'converted']
    if update.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")
        
    try:
        lead.status = update.status
        if update.rm_notes is not None:
            lead.rm_notes = update.rm_notes
        if update.assigned_rm is not None:
            lead.assigned_rm = update.assigned_rm
        lead.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(lead)
        return lead
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update lead: {str(e)}")
