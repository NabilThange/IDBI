"""
Wealth Insights Router
Provides personalized daily/weekly financial insights and opportunities.
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.session_store import session_store
from app.core.cache import cache
from app.core.llm_client import llm_client


router = APIRouter()


class Insight(BaseModel):
    """Single insight"""
    type: str  # opportunity, concern, achievement, tip
    title: str
    message: str
    action: Optional[str] = None
    priority: str  # high, medium, low


class WealthInsightsResponse(BaseModel):
    """Wealth insights response"""
    summary: str
    insights: List[Insight]
    profile_id: str
    cached: bool


def analyze_profile_insights(profile: dict) -> dict:
    """
    Analyze profile to generate insights data.
    Python does the analysis, LLM does the narration.
    
    Args:
        profile: Customer profile
        
    Returns:
        Dictionary with analysis results
    """
    financial = profile.get('financial_summary', {})
    transactions = profile.get('transactions', [])
    goals = profile.get('goals', [])
    current_investments = profile.get('current_investments', [])
    
    # Calculate key metrics
    monthly_income = financial.get('monthly_income', 0)
    monthly_expenses = financial.get('monthly_expenses', 0)
    monthly_savings = financial.get('monthly_savings', 0)
    current_balance = financial.get('current_balance', 0)
    emergency_fund = financial.get('emergency_fund', 0)
    
    # Investable surplus (after current commitments)
    current_sips = sum(
        inv.get('monthly_amount', 0)
        for inv in current_investments
        if inv.get('type') == 'SIP'
    )
    investable_surplus = monthly_savings - current_sips
    
    # Spending analysis (last 30 days)
    spending_by_category = {}
    debit_transactions = [t for t in transactions if t.get('type') == 'debit']
    
    for transaction in debit_transactions:
        category = transaction.get('category', 'other')
        amount = abs(transaction.get('amount', 0))
        spending_by_category[category] = spending_by_category.get(category, 0) + amount
    
    # Find top spending category
    top_category = max(spending_by_category.items(), key=lambda x: x[1]) if spending_by_category else ('none', 0)
    
    # Emergency fund adequacy
    emergency_months = (emergency_fund / monthly_expenses) if monthly_expenses > 0 else 0
    
    # Goal tracking
    high_priority_goals = [g for g in goals if g.get('priority') == 'high']
    
    # Savings rate
    savings_rate = (monthly_savings / monthly_income * 100) if monthly_income > 0 else 0
    
    return {
        "investable_surplus": investable_surplus,
        "savings_rate": round(savings_rate, 1),
        "emergency_months": round(emergency_months, 1),
        "top_spending_category": top_category[0],
        "top_spending_amount": top_category[1],
        "total_monthly_spending": sum(spending_by_category.values()),
        "high_priority_goals_count": len(high_priority_goals),
        "current_balance": current_balance,
        "monthly_income": monthly_income,
        "monthly_expenses": monthly_expenses
    }


def build_insights_prompt(profile: dict, analysis: dict) -> str:
    """
    Build prompt for LLM to generate insights.
    
    Args:
        profile: Customer profile
        analysis: Analysis results from Python
        
    Returns:
        Formatted prompt
    """
    financial = profile.get('financial_summary', {})
    
    prompt = f"""You are a financial advisor for IDBI Bank. Generate personalized wealth insights for this customer.

Customer Profile:
- Name: {profile.get('name')}
- Age: {profile.get('age')}
- Occupation: {profile.get('occupation')}
- Risk Profile: {profile.get('risk_profile')}

Financial Analysis:
- Monthly Income: ₹{analysis['monthly_income']:,}
- Monthly Expenses: ₹{analysis['monthly_expenses']:,}
- Savings Rate: {analysis['savings_rate']}%
- Investable Surplus: ₹{analysis['investable_surplus']:,}
- Current Balance: ₹{analysis['current_balance']:,}
- Emergency Fund Coverage: {analysis['emergency_months']} months
- Top Spending Category: {analysis['top_spending_category']} (₹{analysis['top_spending_amount']:,})
- High Priority Goals: {analysis['high_priority_goals_count']}

Generate 3-5 personalized insights. Include:
1. At least 1 opportunity (investable surplus, savings potential)
2. At least 1 concern if applicable (low emergency fund, high spending)
3. Actionable tips specific to their situation

Provide response in this EXACT JSON format:
{{
  "summary": "2-3 sentence overview of their current financial situation",
  "insights": [
    {{
      "type": "opportunity/concern/achievement/tip",
      "title": "Short catchy title",
      "message": "Detailed explanation with specific numbers",
      "action": "Specific action they can take",
      "priority": "high/medium/low"
    }}
  ]
}}

Guidelines:
- Use actual numbers from their profile
- Be specific and actionable
- Keep tone positive but honest
- Prioritize insights by impact

ONLY return valid JSON, no markdown formatting."""
    
    return prompt


@router.get("/wealth-insights", response_model=WealthInsightsResponse, tags=["AI Endpoints"])
async def get_wealth_insights(
    session_id: str = Query(..., description="Session ID (profile_id)"),
    refresh: bool = Query(False, description="Force refresh cache")
):
    """
    Get personalized wealth insights for the active profile.
    
    This endpoint analyzes the customer's financial situation and provides:
    - Opportunities to invest or save more
    - Concerns about spending or emergency fund
    - Achievements worth celebrating
    - Actionable tips for financial improvement
    
    **No RAG, no tools** - Pure profile analysis + LLM narration.
    Python calculates metrics, LLM provides insights and recommendations.
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
        cached_data = cache.get(profile_id, 'wealth_insights')
        if cached_data:
            response_data = cached_data['data']
            response_data['cached'] = True
            return WealthInsightsResponse(**response_data)
    
    # Analyze profile
    analysis = analyze_profile_insights(profile)
    
    # Build prompt
    prompt = build_insights_prompt(profile, analysis)
    
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
            max_tokens=1200
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
        
        ai_insights = json.loads(llm_response)
        
        # Build response
        response_data = {
            "summary": ai_insights.get('summary', ''),
            "insights": ai_insights.get('insights', []),
            "profile_id": profile_id,
            "cached": False
        }
        
        # Cache
        cache.set(profile_id, 'wealth_insights', response_data)
        
        return WealthInsightsResponse(**response_data)
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing LLM response: {str(e)}. Response was: {llm_response[:200]}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating insights: {str(e)}"
        )
