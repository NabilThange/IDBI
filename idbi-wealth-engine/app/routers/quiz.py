"""
Goal Discovery Quiz Router
Handles quiz submission, status checks, and goal management based on quiz responses
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pathlib import Path

from app.models.quiz import (
    QuizSubmission, QuizResponseData, QuizStatusResponse, 
    QuizQuestionsResponse, GoalUpdateRequest, ComputedGoal,
    RiskProfileComputed, GOAL_TYPE_NAMES, TIMELINE_TO_MONTHS,
    INVESTMENT_RISK_SCORES, VOLATILITY_RISK_SCORES
)
from app.core.database import db, QuizResponse as QuizResponseDB
from app.core.session_store import session_store
from app.config import BASE_DIR

router = APIRouter()


def load_quiz_questions() -> dict:
    """Load quiz questions from config file"""
    quiz_config_path = BASE_DIR / "config" / "quiz_questions.json"
    with open(quiz_config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compute_risk_profile(step3_data: dict, step1_data: dict = None) -> RiskProfileComputed:
    """
    Compute risk profile from Step 3 answers, adjusting for risk capacity 
    derived from dependents, income stability, and protection gap answers.
    """
    investment_pref = step3_data.get('investment_preference')
    volatility_tol = step3_data.get('volatility_tolerance')
    prior_exp = step3_data.get('prior_experience', 'never')
    capacity_loss = step3_data.get('capacity_loss_tolerance', 'manage')
    
    # 1. Compute attitude score (0-100)
    inv_score = INVESTMENT_RISK_SCORES.get(investment_pref, 40)
    vol_score = VOLATILITY_RISK_SCORES.get(volatility_tol, 40)
    attitude_score = (inv_score + vol_score) // 2
    
    risk_score = attitude_score
    capacity_trail = []
    
    # 2. Adjust for capacity if step1_data is provided
    if step1_data:
        dependents = step1_data.get('dependents', 'nobody')
        income_stability = step1_data.get('income_stability', 'fixed')
        health_insurance = step1_data.get('health_insurance', 'employer_only')
        emergency_source = step1_data.get('emergency_source', 'savings')
        
        # Dependents impact
        if dependents in ['spouse', 'parents']:
            risk_score -= 5
            capacity_trail.append("spouse/parents dependents (-5)")
        elif dependents == 'kids':
            risk_score -= 15
            capacity_trail.append("kids dependents (-15)")
        elif dependents in ['multiple', 'a_few_of_these']:
            risk_score -= 20
            capacity_trail.append("multiple dependents (-20)")
            
        # Income stability impact
        if income_stability in ['commission', 'mixed', 'mix_of_these']:
            risk_score -= 10
            capacity_trail.append("commission/variable income (-10)")
        elif income_stability in ['business', 'own_business']:
            risk_score -= 15
            capacity_trail.append("business income (-15)")
            
        # Protection check impact
        if health_insurance == 'no_cover':
            risk_score -= 10
            capacity_trail.append("no health insurance (-10)")
        if emergency_source in ['borrow', 'sell_investments']:
            risk_score -= 10
            capacity_trail.append("weak emergency cover (-10)")
            
    # Loss impact check
    if capacity_loss == 'setback':
        risk_score -= 15
        capacity_trail.append("potential major loss setback (-15)")
        
    # Cap final risk score
    risk_score = max(5, min(95, risk_score))
    
    # Categorize
    if risk_score < 35:
        risk_category = "Conservative"
        explanation = "You prefer safety or have low risk capacity due to family/income constraints. We recommend low-risk products like FDs and debt funds."
    elif risk_score < 65:
        risk_category = "Moderate"
        explanation = "You have balanced risk attitude and capacity. We recommend hybrid portfolios with a mix of stable yields and growth assets."
    else:
        risk_category = "Aggressive"
        explanation = "You have high risk tolerance and strong capacity (steady income, low dependents, solid safety net). We recommend equity mutual funds and growth products."
        
    if capacity_trail:
        explanation += " [Capacity adjustment: " + ", ".join(capacity_trail) + "]"
        
    return RiskProfileComputed(
        risk_category=risk_category,
        risk_score=risk_score,
        investment_preference=investment_pref,
        volatility_tolerance=volatility_tol,
        explanation=explanation
    )


def compute_target_date(timeline: str) -> Optional[str]:
    """
    Compute target date from timeline category
    
    Args:
        timeline: Timeline category (within_1_year, 1_3_years, etc.)
        
    Returns:
        Target date in YYYY-MM-DD format, or None for ongoing goals
    """
    months = TIMELINE_TO_MONTHS.get(timeline)
    if months is None:
        return None
    
    target_date = datetime.now() + timedelta(days=months * 30)
    return target_date.strftime('%Y-%m-%d')


def estimate_current_savings_amount(current_savings_category: str, target_amount: Optional[int]) -> int:
    """
    Estimate current savings amount from category
    
    Args:
        current_savings_category: nothing, less_25, 25_50, more_50, not_sure
        target_amount: Target amount if known
        
    Returns:
        Estimated current savings in INR
    """
    if current_savings_category == "nothing":
        return 0
    
    if target_amount:
        if current_savings_category == "less_25":
            return int(target_amount * 0.125)  # midpoint of 0-25%
        elif current_savings_category == "25_50":
            return int(target_amount * 0.375)  # midpoint of 25-50%
        elif current_savings_category == "more_50":
            return int(target_amount * 0.65)  # midpoint of 50-80%
        elif current_savings_category == "not_sure":
            return int(target_amount * 0.10)  # conservative estimate
    
    # If no target amount, use generic estimates
    generic_estimates = {
        "less_25": 50000,
        "25_50": 150000,
        "more_50": 300000,
        "not_sure": 25000
    }
    
    return generic_estimates.get(current_savings_category, 0)


def compute_monthly_contribution(target_amount: Optional[int], current_savings: int, 
                                  timeline: str, disposable_income: int) -> int:
    """
    Compute recommended monthly contribution for a goal
    
    Args:
        target_amount: Target amount
        current_savings: Current savings
        timeline: Timeline category
        disposable_income: Available monthly disposable income
        
    Returns:
        Recommended monthly contribution in INR
    """
    if not target_amount or timeline == "ongoing":
        # For ongoing goals or unknown targets, suggest 10% of disposable income
        return int(disposable_income * 0.10)
    
    months = TIMELINE_TO_MONTHS.get(timeline, 60)
    if months == 0:
        return 0
    
    remaining_amount = target_amount - current_savings
    if remaining_amount <= 0:
        return 0
    
    required_monthly = int(remaining_amount / months)
    
    # Cap at 80% of disposable income for a single goal
    max_contribution = int(disposable_income * 0.80)
    
    return min(required_monthly, max_contribution)


def compute_new_stats(goals: list, risk_profile: RiskProfileComputed, 
                       profile_data: dict) -> dict:
    """
    Compute additional statistics derived from quiz responses
    
    Args:
        goals: List of ComputedGoal objects
        risk_profile: Computed risk profile
        profile_data: Customer profile data
        
    Returns:
        Dictionary of computed statistics
    """
    financial = profile_data.get('financial_summary', {})
    monthly_income = financial.get('monthly_income', 0)
    monthly_savings = financial.get('monthly_savings', 0)
    
    # Total target amounts
    total_target = sum(g['target_amount'] for g in goals if g['target_amount'])
    total_current_savings = sum(g['current_savings'] for g in goals)
    total_monthly_needed = sum(g['monthly_contribution'] for g in goals)
    
    # Goal Coverage Ratio: current savings / total target
    goal_coverage_ratio = (total_current_savings / total_target * 100) if total_target > 0 else 0
    
    # Savings Velocity: how well monthly savings covers goal requirements
    savings_velocity = (monthly_savings / total_monthly_needed * 100) if total_monthly_needed > 0 else 100
    
    # Multi-Goal Conflict Index: are goals competing for limited resources?
    conflict_index = max(0, min(100, (total_monthly_needed / monthly_savings - 1) * 100)) if monthly_savings > 0 else 100
    
    # Risk-Goal Mismatch: aggressive short-term goals with conservative profile
    short_term_goals = [g for g in goals if g.get('timeline_category') in ['within_1_year', '1_3_years']]
    risk_goal_mismatch = False
    if short_term_goals and risk_profile.risk_category == "Conservative":
        # Conservative investors with aggressive short-term goals may face challenges
        high_target_short_term = any(g.get('target_amount', 0) > monthly_income * 12 for g in short_term_goals)
        if high_target_short_term:
            risk_goal_mismatch = True
    
    # Goal Urgency Scores
    goal_urgency_scores = {}
    for goal in goals:
        timeline = goal.get('timeline_category', '')
        priority = goal.get('priority', 3)
        progress = (goal['current_savings'] / goal['target_amount'] * 100) if goal.get('target_amount', 0) > 0 else 50
        
        # Urgency = (timeline weight) + (priority weight) + (progress gap weight)
        timeline_weight = {
            'within_1_year': 50,
            '1_3_years': 35,
            '3_5_years': 20,
            '5_10_years': 10,
            '10_plus_years': 5,
            'ongoing': 0
        }.get(timeline, 10)
        
        priority_weight = (4 - priority) * 15  # priority 1 = 45, 2 = 30, 3 = 15
        progress_gap_weight = max(0, 100 - progress) * 0.2  # more gap = higher urgency
        
        urgency_score = int(timeline_weight + priority_weight + progress_gap_weight)
        goal_urgency_scores[goal['goal_id']] = min(100, urgency_score)
    
    return {
        "total_target_amount": total_target,
        "total_current_savings": total_current_savings,
        "total_monthly_contribution_needed": total_monthly_needed,
        "goal_coverage_ratio": round(goal_coverage_ratio, 1),
        "savings_velocity": round(savings_velocity, 1),
        "multi_goal_conflict_index": round(conflict_index, 1),
        "risk_goal_mismatch_alert": risk_goal_mismatch,
        "goal_urgency_scores": goal_urgency_scores,
        "monthly_savings_surplus_deficit": monthly_savings - total_monthly_needed
    }


@router.get("/quiz/questions", response_model=QuizQuestionsResponse, tags=["Quiz"])
async def get_quiz_questions():
    """
    Get quiz questions structure for frontend
    
    Returns the complete quiz configuration including all questions,
    options, and conditional logic.
    """
    questions = load_quiz_questions()
    return QuizQuestionsResponse(**questions)


@router.get("/quiz/status", response_model=QuizStatusResponse, tags=["Quiz"])
async def get_quiz_status(
    session_id: str = Query(..., description="Session ID (profile_id)")
):
    """
    Check if customer has completed the quiz and if it needs refresh
    
    Quiz should be refreshed:
    - If never completed (mandatory for first-time users)
    - If completed > 365 days ago (annual refresh)
    - After life-event detection (handled separately)
    """
    # Get active profile
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}"
        )
    
    customer_id = profile['profile_id']
    
    # Check database for quiz response
    session = db.get_session()
    try:
        quiz_response = session.query(QuizResponseDB).filter(
            QuizResponseDB.customer_id == customer_id
        ).first()
        
        if not quiz_response:
            return QuizStatusResponse(
                customer_id=customer_id,
                quiz_completed=False,
                quiz_completed_at=None,
                needs_refresh=True,
                days_since_completion=None
            )
        
        # Check if needs refresh (> 365 days)
        completed_at = quiz_response.completed_at
        days_since = (datetime.now() - completed_at).days
        needs_refresh = days_since > 365
        
        return QuizStatusResponse(
            customer_id=customer_id,
            quiz_completed=True,
            quiz_completed_at=completed_at.isoformat(),
            needs_refresh=needs_refresh,
            days_since_completion=days_since
        )
        
    finally:
        session.close()


@router.post("/quiz/submit", response_model=QuizResponseData, tags=["Quiz"])
async def submit_quiz(
    submission: QuizSubmission
):
    """
    Submit completed quiz and process responses
    
    This endpoint:
    1. Validates quiz responses
    2. Computes risk profile from Step 3
    3. Processes goals from Step 2 with timelines and targets
    4. Computes additional statistics (coverage ratio, urgency scores, etc.)
    5. Stores in database
    6. Returns processed data for immediate use
    
    **This is the foundational endpoint** - all recommendations, goal tracking,
    and suitability computations depend on this quiz data.
    """
    customer_id = submission.customer_id
    
    # Get customer profile for disposable income calculation
    profile = session_store.get_profile_by_id(customer_id)
    if not profile:
        # Fallback: Load profile from JSON file
        from app.config import PROFILES_DIR
        for profile_file in PROFILES_DIR.glob("*.json"):
            try:
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                    if profile_data.get('profile_id') == customer_id:
                        profile = profile_data
                        # Store in session store so it's active
                        session_store.set_active_profile(customer_id, profile)
                        break
            except Exception:
                continue
                
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Customer profile {customer_id} not found"
        )
    
    financial = profile.get('financial_summary', {})
    disposable_income = financial.get('monthly_savings', 0)
    
    # Compute risk profile from Step 3 (adjusting for Step 1 capacity)
    risk_profile = compute_risk_profile(submission.step3.dict(), submission.step1.dict())
    
    # Process goals from Step 2
    computed_goals = []
    for idx, goal_detail in enumerate(submission.step2.goals):
        goal_type = goal_detail.goal_type
        goal_name = GOAL_TYPE_NAMES.get(goal_type, goal_type.replace('_', ' ').title())
        
        target_date = compute_target_date(goal_detail.timeline)
        # Direct rupee savings from user input
        current_savings = goal_detail.current_savings
        
        # For goals with known target, compute monthly contribution
        monthly_contribution = compute_monthly_contribution(
            goal_detail.target_amount,
            current_savings,
            goal_detail.timeline,
            disposable_income
        )
        
        computed_goal = ComputedGoal(
            goal_id=f"goal_{goal_type}_{idx+1}",
            goal_type=goal_type,
            goal_name=goal_name,
            name=goal_name,
            target_amount=goal_detail.target_amount,
            target_date=target_date,
            current_savings=current_savings,
            monthly_contribution=monthly_contribution,
            priority=goal_detail.priority,
            timeline_category=goal_detail.timeline,
            status="active"
        )
        
        computed_goals.append(computed_goal)
    
    # Sort goals by priority
    computed_goals.sort(key=lambda g: g.priority)
    
    # Compute additional statistics
    goals_dict = [g.dict() for g in computed_goals]
    new_stats = compute_new_stats(goals_dict, risk_profile, profile)
    
    # Pack Step 1 and Step 3 metadata into new_stats
    new_stats["dependents"] = submission.step1.dependents
    new_stats["income_stability"] = submission.step1.income_stability
    new_stats["health_insurance"] = submission.step1.health_insurance
    new_stats["emergency_source"] = submission.step1.emergency_source
    new_stats["prior_experience"] = submission.step3.prior_experience
    new_stats["capacity_loss_tolerance"] = submission.step3.capacity_loss_tolerance

    # Build response
    response_data = QuizResponseData(
        customer_id=customer_id,
        quiz_version="v1.0",
        life_stage=submission.step1.life_stage,
        priorities=submission.step1.priorities,
        dependents=submission.step1.dependents,
        income_stability=submission.step1.income_stability,
        health_insurance=submission.step1.health_insurance,
        emergency_source=submission.step1.emergency_source,
        prior_experience=submission.step3.prior_experience,
        capacity_loss_tolerance=submission.step3.capacity_loss_tolerance,
        goals=computed_goals,
        risk_profile=risk_profile,
        quiz_completed_at=datetime.now().isoformat(),
        new_stats=new_stats
    )
    
    # Store in database
    session = db.get_session()
    try:
        # Check if quiz already exists for this customer
        existing_quiz = session.query(QuizResponseDB).filter(
            QuizResponseDB.customer_id == customer_id
        ).first()
        
        if existing_quiz:
            # Update existing
            existing_quiz.quiz_version = "v1.0"
            existing_quiz.life_stage = submission.step1.life_stage
            existing_quiz.priorities = submission.step1.priorities
            existing_quiz.goals = goals_dict
            existing_quiz.risk_profile = risk_profile.dict()
            existing_quiz.computed_stats = new_stats
            existing_quiz.updated_at = datetime.now()
        else:
            # Create new
            new_quiz = QuizResponseDB(
                customer_id=customer_id,
                quiz_version="v1.0",
                life_stage=submission.step1.life_stage,
                priorities=submission.step1.priorities,
                goals=goals_dict,
                risk_profile=risk_profile.dict(),
                computed_stats=new_stats,
                completed_at=datetime.now()
            )
            session.add(new_quiz)
        
        session.commit()
        
        # Update session store with new quiz results
        if profile:
            profile['goals'] = goals_dict
            profile['risk_profile'] = risk_profile.dict()
            profile['life_stage'] = submission.step1.life_stage
            profile['priorities'] = submission.step1.priorities
            session_store.set_active_profile(customer_id, profile)
            
        # Invalidate cache for this customer
        from app.core.cache import cache
        cache.invalidate(customer_id)
        
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error saving quiz response: {str(e)}"
        )
    finally:
        session.close()
    
    return response_data


@router.get("/quiz/response", response_model=QuizResponseData, tags=["Quiz"])
async def get_quiz_response(
    session_id: str = Query(..., description="Session ID (profile_id)")
):
    """
    Get stored quiz response for a customer
    
    Returns the processed quiz data including computed goals, risk profile,
    and additional statistics.
    """
    # Get active profile
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}"
        )
    
    customer_id = profile['profile_id']
    
    # Get quiz response from database
    session = db.get_session()
    try:
        quiz_response = session.query(QuizResponseDB).filter(
            QuizResponseDB.customer_id == customer_id
        ).first()
        
        if not quiz_response:
            raise HTTPException(
                status_code=404,
                detail=f"No quiz response found for customer {customer_id}. Please complete the quiz first."
            )
        
        # Build response
        goals = [ComputedGoal(**g) for g in quiz_response.goals]
        risk_profile = RiskProfileComputed(**quiz_response.risk_profile)
        stats = quiz_response.computed_stats or {}
        
        return QuizResponseData(
            customer_id=customer_id,
            quiz_version=quiz_response.quiz_version,
            life_stage=quiz_response.life_stage,
            priorities=quiz_response.priorities,
            dependents=stats.get("dependents", "nobody"),
            income_stability=stats.get("income_stability", "fixed"),
            health_insurance=stats.get("health_insurance", "employer_only"),
            emergency_source=stats.get("emergency_source", "savings"),
            prior_experience=stats.get("prior_experience", "never"),
            capacity_loss_tolerance=stats.get("capacity_loss_tolerance", "manage"),
            goals=goals,
            risk_profile=risk_profile,
            quiz_completed_at=quiz_response.completed_at.isoformat(),
            new_stats=stats
        )
        
    finally:
        session.close()


@router.put("/goals/{goal_id}", tags=["Quiz"])
async def update_goal(
    goal_id: str,
    goal_update: GoalUpdateRequest,
    session_id: str = Query(..., description="Session ID (profile_id)")
):
    """
    Update a specific goal's parameters
    
    Allows customer to update target amount, target date, current savings,
    monthly contribution, or priority for a specific goal.
    """
    # Get active profile
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}"
        )
    
    customer_id = profile['profile_id']
    
    # Get quiz response
    session = db.get_session()
    try:
        quiz_response = session.query(QuizResponseDB).filter(
            QuizResponseDB.customer_id == customer_id
        ).first()
        
        if not quiz_response:
            raise HTTPException(
                status_code=404,
                detail=f"No quiz response found for customer {customer_id}"
            )
        
        # Find and update goal
        goals = quiz_response.goals
        goal_found = False
        
        for goal in goals:
            if goal['goal_id'] == goal_id:
                goal_found = True
                
                # Update fields if provided
                if goal_update.target_amount is not None:
                    goal['target_amount'] = goal_update.target_amount
                if goal_update.target_date is not None:
                    goal['target_date'] = goal_update.target_date
                if goal_update.current_savings is not None:
                    goal['current_savings'] = goal_update.current_savings
                if goal_update.monthly_contribution is not None:
                    goal['monthly_contribution'] = goal_update.monthly_contribution
                if goal_update.priority is not None:
                    goal['priority'] = goal_update.priority
                if goal_update.status is not None:
                    goal['status'] = goal_update.status
                
                break
        
        if not goal_found:
            raise HTTPException(
                status_code=404,
                detail=f"Goal {goal_id} not found for customer {customer_id}"
            )
        
        # Recompute statistics
        risk_profile = RiskProfileComputed(**quiz_response.risk_profile)
        new_stats = compute_new_stats(goals, risk_profile, profile)
        quiz_response.computed_stats = new_stats
        
        # Update timestamp
        quiz_response.updated_at = datetime.now()
        
        session.commit()
        
        # Update session store
        profile['goals'] = goals
        profile['computed_stats'] = new_stats
        session_store.set_active_profile(session_id, profile)
        
        # Invalidate cache
        from app.core.cache import cache
        cache.invalidate(customer_id)
        
        return {
            "status": "success",
            "message": f"Goal {goal_id} updated successfully",
            "updated_goal": goal,
            "new_stats": new_stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error updating goal: {str(e)}"
        )
    finally:
        session.close()
