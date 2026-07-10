"""
Tool: Calculate Goal Projection
Calculates financial goal progress and projections.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime
from dateutil.relativedelta import relativedelta

from app.core.session_store import session_store


# Tool definition for Groq
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "calculate_goal_projection",
        "description": "Calculate progress and projection for a specific financial goal. Returns current status, target date, monthly contribution needed, and whether the customer is on track. Use this when discussing specific goals or providing goal advice.",
        "parameters": {
            "type": "object",
            "properties": {
                "goal_name": {
                    "type": "string",
                    "description": "Name of the goal to analyze (e.g., 'Emergency Fund', 'House Down Payment', 'Retirement Corpus')"
                }
            },
            "required": ["goal_name"]
        }
    }
}


def calculate_goal_projection(goal_name: str) -> Dict[str, Any]:
    """
    Calculate goal progress and projection with pure Python math.
    
    Args:
        goal_name: Name of the goal to analyze (case-insensitive match)
        
    Returns:
        Dictionary containing goal projection details
        
    Raises:
        ValueError: If no customer session is active or goal not found
    """
    profile = session_store.get_profile()
    
    if not profile:
        raise ValueError("No customer profile selected. Please select a profile first.")
    
    goals = profile.get("goals", [])
    
    # Find matching goal (case-insensitive)
    goal = None
    goal_name_lower = goal_name.lower()
    for g in goals:
        if g.get("name", "").lower() == goal_name_lower:
            goal = g
            break
    
    if not goal:
        available_goals = [g.get("name") for g in goals]
        raise ValueError(
            f"Goal '{goal_name}' not found. Available goals: {', '.join(available_goals)}"
        )
    
    # Extract goal data
    goal_id = goal.get("goal_id", "unknown")
    name = goal.get("name")
    target_amount = goal.get("target_amount", 0)
    current_savings = goal.get("current_savings", 0)
    monthly_contribution = goal.get("monthly_contribution", 0)
    target_date_str = goal.get("target_date")
    
    # Calculate progress
    progress_percent = (current_savings / target_amount * 100) if target_amount > 0 else 0
    remaining_amount = target_amount - current_savings
    
    # Calculate time to target
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m")
        today = datetime.now()
        months_to_target = (target_date.year - today.year) * 12 + (target_date.month - today.month)
    except:
        months_to_target = 12  # Default fallback
    
    # Calculate required monthly contribution
    if months_to_target > 0 and remaining_amount > 0:
        required_monthly = remaining_amount / months_to_target
    else:
        required_monthly = 0
    
    # Calculate projected completion date with current contribution
    if monthly_contribution > 0 and remaining_amount > 0:
        projected_months = remaining_amount / monthly_contribution
        projected_date = datetime.now() + relativedelta(months=int(projected_months))
        projected_date_str = projected_date.strftime("%Y-%m")
        gap_months = int(projected_months) - months_to_target
    else:
        projected_date_str = None
        gap_months = None
    
    # Determine status
    if progress_percent >= 100:
        status = "completed"
    elif gap_months is None:
        status = "unknown"
    elif gap_months <= 0:
        status = "ahead_schedule"
    elif gap_months <= 3:
        status = "on_track"
    else:
        status = "behind_schedule"
    
    return {
        "goal_id": goal_id,
        "name": name,
        "target_amount": target_amount,
        "current_savings": current_savings,
        "remaining_amount": remaining_amount,
        "progress_percent": round(progress_percent, 2),
        "target_date": target_date_str,
        "months_remaining": months_to_target,
        "current_monthly_contribution": monthly_contribution,
        "required_monthly_contribution": round(required_monthly, 2),
        "shortfall_per_month": round(required_monthly - monthly_contribution, 2) if required_monthly > monthly_contribution else 0,
        "projected_completion_date": projected_date_str,
        "gap_months": gap_months,
        "status": status,
        "status_description": {
            "completed": "Goal has been achieved",
            "ahead_schedule": "On track to complete ahead of target date",
            "on_track": "Making good progress toward target date",
            "behind_schedule": "Need to increase contributions to meet target date",
            "unknown": "Unable to calculate projection"
        }.get(status, "Unknown status")
    }
