"""
Financial Health Router
Provides AI-powered financial wellness assessment.
"""

import json
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.session_store import session_store
from app.core.cache import cache
from app.core.llm_client import llm_client
from app.core.rules_engine import rules_engine


router = APIRouter()


class FinancialHealthResponse(BaseModel):
    """Financial health assessment response"""
    status: str
    score: int
    grade: str
    summary: str
    strengths: list[str]
    concerns: list[str]
    recommendations: list[str]
    profile_id: str
    cached: bool


def calculate_financial_health_score(profile: dict) -> dict:
    """
    Calculate basic financial health metrics using Python.
    LLM will only provide narrative/interpretation.
    
    Uses rules from app/config/financial_health_rules.json
    
    Args:
        profile: Customer profile data
        
    Returns:
        Dictionary with calculated metrics
    """
    financial = profile.get('financial_summary', {})
    
    # Calculate savings ratio
    income = financial.get('monthly_income', 1)
    savings = financial.get('monthly_savings', 0)
    savings_ratio = (savings / income * 100) if income > 0 else 0
    
    # Emergency fund adequacy (should cover 6 months expenses)
    expenses = financial.get('monthly_expenses', 0)
    emergency_fund = financial.get('emergency_fund', 0)
    emergency_months = (emergency_fund / expenses) if expenses > 0 else 0
    
    # Investment ratio
    investments = financial.get('total_investments', 0)
    investment_ratio = (investments / (income * 12)) if income > 0 else 0
    
    # Debt analysis
    loans = profile.get('loans', [])
    total_debt = sum(loan.get('outstanding_amount', 0) for loan in loans)
    debt_to_income = (total_debt / (income * 12)) if income > 0 else 0
    
    # Prepare metrics for rules engine
    metrics = {
        'savings_ratio': savings_ratio,
        'emergency_fund_months': emergency_months,
        'investment_ratio': investment_ratio,
        'debt_to_income': debt_to_income
    }
    
    # Calculate score using rules engine (loaded from JSON config)
    score = rules_engine.calculate_total_score(metrics)
    grade = rules_engine.get_grade(score)
    
    return {
        "score": score,
        "grade": grade,
        "savings_ratio": round(savings_ratio, 1),
        "emergency_months": round(emergency_months, 1),
        "investment_ratio": round(investment_ratio, 2),
        "debt_to_income": round(debt_to_income, 2),
        "total_debt": total_debt,
        "rules_version": rules_engine.get_rules_version()
    }


def build_financial_health_prompt(profile: dict, metrics: dict) -> str:
    """
    Build prompt for LLM to generate narrative assessment.
    
    Args:
        profile: Customer profile data
        metrics: Calculated financial metrics
        
    Returns:
        Formatted prompt string
    """
    financial = profile.get('financial_summary', {})
    
    prompt = f"""You are a financial advisor for IDBI Bank. Analyze this customer's financial health.

Customer Profile:
- Name: {profile.get('name')}
- Age: {profile.get('age')}
- Occupation: {profile.get('occupation')}
- Risk Profile: {profile.get('risk_profile')}

Financial Summary:
- Monthly Income: ₹{financial.get('monthly_income'):,}
- Monthly Expenses: ₹{financial.get('monthly_expenses'):,}
- Monthly Savings: ₹{financial.get('monthly_savings'):,}
- Current Balance: ₹{financial.get('current_balance'):,}
- Emergency Fund: ₹{financial.get('emergency_fund'):,}
- Total Investments: ₹{financial.get('total_investments'):,}

Calculated Metrics:
- Financial Health Score: {metrics['score']}/100 (Grade: {metrics['grade']})
- Savings Ratio: {metrics['savings_ratio']}%
- Emergency Fund Coverage: {metrics['emergency_months']} months
- Investment to Income Ratio: {metrics['investment_ratio']}x
- Debt to Income Ratio: {metrics['debt_to_income']}x

Loans: {json.dumps(profile.get('loans', []), indent=2)}

Goals: {json.dumps(profile.get('goals', []), indent=2)}

Provide a JSON response with this EXACT structure:
{{
  "summary": "2-3 sentence overview of their financial health",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "concerns": ["concern 1", "concern 2"],
  "recommendations": ["recommendation 1", "recommendation 2", "recommendation 3"]
}}

Be specific, actionable, and personalized. Reference actual numbers from their profile.
ONLY return valid JSON, no markdown formatting or extra text."""
    
    return prompt


@router.get("/financial-health", response_model=FinancialHealthResponse, tags=["AI Endpoints"])
async def get_financial_health(
    session_id: str = Query(..., description="Session ID (profile_id)"),
    refresh: bool = Query(False, description="Force refresh cache")
):
    """
    Get AI-powered financial health assessment for the active profile.
    
    This endpoint:
    1. Retrieves the active profile from session
    2. Calculates financial metrics using Python
    3. Uses LLM to generate personalized narrative
    4. Caches the result for future requests
    5. Returns comprehensive financial health assessment
    
    **No RAG, no tools** - just profile data + LLM reasoning.
    """
    # Get active profile
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}. Please select a profile first."
        )
    
    profile_id = profile['profile_id']
    
    # Check cache (unless refresh requested)
    if not refresh:
        cached_data = cache.get(profile_id, 'financial_health')
        if cached_data:
            response_data = cached_data['data']
            response_data['cached'] = True
            return FinancialHealthResponse(**response_data)
    
    # Calculate metrics
    metrics = calculate_financial_health_score(profile)
    
    # Build prompt
    prompt = build_financial_health_prompt(profile, metrics)
    
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
        
        # Parse LLM response
        # Clean potential markdown formatting
        llm_response = llm_response.strip()
        if llm_response.startswith("```json"):
            llm_response = llm_response[7:]
        if llm_response.startswith("```"):
            llm_response = llm_response[3:]
        if llm_response.endswith("```"):
            llm_response = llm_response[:-3]
        llm_response = llm_response.strip()
        
        ai_assessment = json.loads(llm_response)
        
        # Build response
        response_data = {
            "status": "healthy" if metrics['score'] >= 60 else "needs_attention",
            "score": metrics['score'],
            "grade": metrics['grade'],
            "summary": ai_assessment.get('summary', ''),
            "strengths": ai_assessment.get('strengths', []),
            "concerns": ai_assessment.get('concerns', []),
            "recommendations": ai_assessment.get('recommendations', []),
            "profile_id": profile_id,
            "cached": False
        }
        
        # Cache the response
        cache.set(profile_id, 'financial_health', response_data)
        
        return FinancialHealthResponse(**response_data)
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing LLM response: {str(e)}. Response was: {llm_response[:200]}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating financial health assessment: {str(e)}"
        )
