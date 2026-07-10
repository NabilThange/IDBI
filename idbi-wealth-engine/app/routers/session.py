"""
Session Management Router
Handles profile selection and session management.
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import PROFILES_DIR
from app.core.session_store import session_store

router = APIRouter()


class ProfileSummary(BaseModel):
    """Summary of a customer profile"""
    profile_id: str
    name: str
    age: int
    occupation: str
    city: str
    risk_profile: str  # Will extract risk_category from dict
    monthly_income: int
    monthly_savings: int


class SessionSelectRequest(BaseModel):
    """Request body for selecting a profile"""
    profile_id: str


class SessionSelectResponse(BaseModel):
    """Response after selecting a profile"""
    status: str
    message: str
    profile_id: str
    session_id: str


def load_profile(profile_id: str) -> Dict[str, Any]:
    """
    Load a profile from JSON file.
    
    Args:
        profile_id: Profile identifier
        
    Returns:
        Profile data dictionary
        
    Raises:
        FileNotFoundError: If profile file doesn't exist
    """
    # Try to find profile file by ID
    for profile_file in PROFILES_DIR.glob("*.json"):
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                if profile_data.get('profile_id') == profile_id:
                    return profile_data
        except Exception as e:
            print(f"Error reading {profile_file}: {e}")
            continue
    
    raise FileNotFoundError(f"Profile {profile_id} not found")


@router.get("/profiles", response_model=List[ProfileSummary], tags=["Session"])
async def list_profiles():
    """
    List all available demo profiles.
    Returns summary information for profile selection.
    """
    profiles = []
    
    # Read all profile JSON files
    for profile_file in PROFILES_DIR.glob("*.json"):
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
                
                # Extract risk_category from risk_profile dict
                risk_profile = profile_data.get('risk_profile', {})
                if isinstance(risk_profile, dict):
                    risk_category = risk_profile.get('risk_category', 'Moderate')
                else:
                    risk_category = str(risk_profile)
                
                # Extract summary information
                profiles.append(ProfileSummary(
                    profile_id=profile_data['profile_id'],
                    name=profile_data['name'],
                    age=profile_data['age'],
                    occupation=profile_data['occupation'],
                    city=profile_data['city'],
                    risk_profile=risk_category,
                    monthly_income=profile_data['financial_summary']['monthly_income'],
                    monthly_savings=profile_data['financial_summary']['monthly_savings']
                ))
        except Exception as e:
            print(f"Error reading profile {profile_file}: {e}")
            continue
    
    if not profiles:
        raise HTTPException(
            status_code=404,
            detail="No profiles found. Please ensure profile JSON files exist in app/profiles/"
        )
    
    return profiles


@router.post("/session/select", response_model=SessionSelectResponse, tags=["Session"])
async def select_profile(request: SessionSelectRequest):
    """
    Select a profile to activate for the current session.
    This loads the profile into memory and initializes chat history.
    """
    try:
        # Load profile data
        profile_data = load_profile(request.profile_id)
        
        # Merge quiz response from database if it exists
        from app.core.database import db, QuizResponse as QuizResponseDB
        db_session = db.get_session()
        try:
            quiz_resp = db_session.query(QuizResponseDB).filter(
                QuizResponseDB.customer_id == request.profile_id
            ).first()
            if quiz_resp:
                profile_data['goals'] = quiz_resp.goals
                profile_data['risk_profile'] = quiz_resp.risk_profile
                profile_data['life_stage'] = quiz_resp.life_stage
                profile_data['priorities'] = quiz_resp.priorities
                if quiz_resp.computed_stats:
                    profile_data['computed_stats'] = quiz_resp.computed_stats
        except Exception as e:
            print(f"Error merging quiz response: {e}")
        finally:
            db_session.close()
        
        # Store in session
        session_id = request.profile_id  # Using profile_id as session_id for simplicity
        session_store.set_active_profile(session_id, profile_data)
        
        return SessionSelectResponse(
            status="success",
            message=f"Profile {profile_data['name']} activated successfully",
            profile_id=request.profile_id,
            session_id=session_id
        )
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Profile {request.profile_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading profile: {str(e)}"
        )


@router.get("/session/current/{session_id}", tags=["Session"])
async def get_current_session(session_id: str):
    """
    Get the currently active profile for a session.
    Returns full profile data.
    """
    profile = session_store.get_active_profile(session_id)
    
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}. Please select a profile first."
        )
    
    return {
        "status": "active",
        "session_id": session_id,
        "profile": profile
    }


@router.delete("/session/{session_id}", tags=["Session"])
async def clear_session(session_id: str):
    """
    Clear a session (remove active profile and chat history).
    """
    session_store.clear_session(session_id)
    
    return {
        "status": "success",
        "message": f"Session {session_id} cleared",
        "session_id": session_id
    }
