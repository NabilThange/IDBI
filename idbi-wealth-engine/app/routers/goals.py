"""
Goal Progress Router
Tracks progress toward financial goals with projections.
"""

import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.session_store import session_store
from app.core.cache import cache
from app.core.llm_client import llm_client


router = APIRouter()


class GoalProgress(BaseModel):
    """Single goal progress"""
    goal_id: str
    name: str
    target_amount: int
    current_savings: int
    progress_percent: float
    status: str  # on_track, behind_schedule, ahead_schedule, completed
    projected_completion: Optional[str] = None
    target_date: str
    gap_months: Optional[int] = None
    monthly_contribution: int
    recommended_contribution: Optional[int] = None
    recommendation: str


class GoalProgressResponse(BaseModel):
    """Goal progress response"""
    summary: str
    goals: List[GoalProgress]
    profile_id: str
    cached: bool


def calculate_goal_projection(goal: dict) -> dict:
    """
    Calculate goal progress and projection.
    Pure Python calculations - no LLM.
    
    Args:
        goal: Goal data from profile
        
    Returns:
        Dictionary with projections
    """
    target_amount = goal.get('target_amount', 0)
    target_date_str = goal.get('target_date', '')
    current_savings = goal.get('current_savings', 0)
    monthly_contribution = goal.get('monthly_contribution', 0)
    
    # Parse target date
    try:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    except:
        target_date = datetime.now()
    
    today = datetime.now()
    months_remaining = max(0, (target_date.year - today.year) * 12 + (target_date.month - today.month))
    
    # Progress percentage
    progress_percent = (current_savings / target_amount * 100) if target_amount > 0 else 0
    
    # Projection at current contribution rate
    if monthly_contribution > 0:
        total_at_target = current_savings + (monthly_contribution * months_remaining)
        
        if total_at_target >= target_amount:
            status = "on_track"
            # Calculate actual completion month
            months_needed = max(0, int((target_amount - current_savings) / monthly_contribution))
            projected_date = datetime(today.year, today.month, 1)
            
            # Add months
            year_add = months_needed // 12
            month_add = months_needed % 12
            projected_year = projected_date.year + year_add
            projected_month = projected_date.month + month_add
            
            if projected_month > 12:
                projected_year += 1
                projected_month -= 12
            
            projected_completion = f"{projected_year}-{projected_month:02d}-01"
            gap_months = None
            recommended_contribution = monthly_contribution
            
        else:
            status = "behind_schedule"
            shortfall = target_amount - total_at_target
            
            # Calculate required monthly contribution
            if months_remaining > 0:
                recommended_contribution = int((target_amount - current_savings) / months_remaining)
            else:
                recommended_contribution = target_amount - current_savings
            
            # Calculate months behind
            months_with_shortfall = int(shortfall / monthly_contribution) if monthly_contribution > 0 else 0
            gap_months = months_with_shortfall
            
            # Projected completion with current rate
            total_months_needed = int((target_amount - current_savings) / monthly_contribution) if monthly_contribution > 0 else 999
            projected_year = today.year + (total_months_needed // 12)
            projected_month = today.month + (total_months_needed % 12)
            
            if projected_month > 12:
                projected_year += 1
                projected_month -= 12
            
            projected_completion = f"{projected_year}-{projected_month:02d}-01"
    else:
        status = "no_contribution"
        projected_completion = None
        gap_months = months_remaining
        recommended_contribution = int((target_amount - current_savings) / months_remaining) if months_remaining > 0 else 0
    
    # Check if completed
    if progress_percent >= 100:
        status = "completed"
    
    return {
        "goal_id": goal.get('goal_id'),
        "name": goal.get('name') or goal.get('goal_name', ''),
        "target_amount": target_amount,
        "current_savings": current_savings,
        "progress_percent": round(progress_percent, 1),
        "status": status,
        "projected_completion": projected_completion,
        "target_date": target_date_str,
        "gap_months": gap_months,
        "monthly_contribution": monthly_contribution,
        "recommended_contribution": recommended_contribution,
        "months_remaining": months_remaining
    }


def build_goal_prompt(profile: dict, projections: List[dict]) -> str:
    """
    Build prompt for LLM to generate goal recommendations.
    
    Args:
        profile: Customer profile
        projections: Goal projections from Python
        
    Returns:
        Formatted prompt
    """
    financial = profile.get('financial_summary', {})
    
    prompt = f"""You are a financial advisor for IDBI Bank. Analyze this customer's goal progress and provide recommendations.

Customer Profile:
- Name: {profile.get('name')}
- Age: {profile.get('age')}
- Monthly Income: ₹{financial.get('monthly_income'):,}
- Monthly Savings: ₹{financial.get('monthly_savings'):,}

Goal Analysis:
{json.dumps(projections, indent=2)}

For each goal, provide a specific recommendation on how to get back on track or optimize progress.

Provide response in this EXACT JSON format:
{{
  "summary": "2-3 sentence overview of goal progress status",
  "goal_recommendations": {{
    "goal_id_1": "Specific recommendation with numbers and timeline",
    "goal_id_2": "Specific recommendation with numbers and timeline"
  }}
}}

Guidelines:
- Be specific with amounts and timelines
- Consider their total monthly savings capacity
- Prioritize high priority goals
- Suggest realistic adjustments

ONLY return valid JSON, no markdown formatting."""
    
    return prompt


@router.get("/goal-progress", response_model=GoalProgressResponse, tags=["AI Endpoints"])
async def get_goal_progress(
    session_id: str = Query(..., description="Session ID (profile_id)"),
    refresh: bool = Query(False, description="Force refresh cache")
):
    """
    Get financial goal progress tracking with projections.
    
    This endpoint analyzes each goal to provide:
    - Current progress percentage
    - On-track vs behind-schedule status
    - Projected completion date at current contribution rate
    - Recommended contribution to meet target on time
    - Specific recommendations to optimize progress
    
    **No RAG, no tools** - Pure goal math + LLM recommendations.
    Python calculates all projections, LLM provides actionable advice.
    """
    # Get active profile
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}. Please select a profile first."
        )
    
    profile_id = profile['profile_id']
    
    # Check cache
    if not refresh:
        cached_data = cache.get(profile_id, 'goal_progress')
        if cached_data:
            response_data = cached_data['data']
            response_data['cached'] = True
            return GoalProgressResponse(**response_data)
    
    # Get goals
    goals = profile.get('goals', [])
    
    if not goals:
        raise HTTPException(
            status_code=404,
            detail="No goals found for this profile"
        )
    
    # Calculate projections for each goal
    projections = []
    for goal in goals:
        projection = calculate_goal_projection(goal)
        projections.append(projection)
    
    # Build prompt
    prompt = build_goal_prompt(profile, projections)
    
    # Call LLM
    try:
        system_prompt = (
            "You are an expert financial advisor for IDBI Bank. "
            "Always respond with valid JSON only. "
            "Any text inside the JSON that the customer will read (reasoning, description, notes, insights) "
            "must use simple, everyday English — short sentences, no jargon left unexplained, rounded numbers "
            "with a relatable comparison where useful, and a warm tone like a trusted advisor who knows the customer well."
        )
        
        llm_response = llm_client.chat_with_system(
            system_prompt=system_prompt,
            user_message=prompt,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Parse response
        llm_response = llm_response.strip()
        if llm_response.startswith("```json"):
            llm_response = llm_response[7:]
        if llm_response.startswith("```"):
            llm_response = llm_response[3:]
        if llm_response.endswith("```"):
            llm_response = llm_response[:-3]
        llm_response = llm_response.strip()
        
        ai_recommendations = json.loads(llm_response)
        
        # Merge projections with LLM recommendations
        goal_recs = ai_recommendations.get('goal_recommendations', {})
        
        goals_with_recs = []
        for projection in projections:
            goal_id = projection['goal_id']
            projection['recommendation'] = goal_recs.get(goal_id, "Continue with current contributions")
            goals_with_recs.append(projection)
        
        # Build response
        response_data = {
            "summary": ai_recommendations.get('summary', ''),
            "goals": goals_with_recs,
            "profile_id": profile_id,
            "cached": False
        }
        
        # Cache
        cache.set(profile_id, 'goal_progress', response_data)
        
        return GoalProgressResponse(**response_data)
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing LLM response: {str(e)}. Response was: {llm_response[:200]}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating goal progress: {str(e)}"
        )
