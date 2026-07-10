"""
Spending Analysis Router
Categorizes and analyzes transaction patterns.
"""

import json
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.session_store import session_store
from app.core.cache import cache
from app.core.llm_client import llm_client


router = APIRouter()


class CategorySpending(BaseModel):
    """Spending by category"""
    category: str
    amount: int
    percent: float
    transaction_count: int


class SpendingTrend(BaseModel):
    """Spending trend for a category"""
    category: str
    current_amount: int
    trend: str  # increasing, decreasing, stable
    alert: Optional[str] = None


class MerchantSpending(BaseModel):
    """Top merchant spending"""
    name: str
    amount: int
    transaction_count: int
    category: str


class SpendingAnalysisResponse(BaseModel):
    """Spending analysis response"""
    summary: str
    total_spent: int
    spending_by_category: List[CategorySpending]
    trends: List[SpendingTrend]
    top_merchants: List[MerchantSpending]
    recommendations: List[str]
    profile_id: str
    cached: bool


def analyze_spending(profile: dict) -> Dict:
    """
    Analyze transaction patterns.
    Python does all calculations.
    
    Args:
        profile: Customer profile
        
    Returns:
        Spending analysis data
    """
    transactions = profile.get('transactions', [])
    
    # Filter debit transactions
    debit_txns = [t for t in transactions if t.get('type') == 'debit']
    
    # Category analysis
    category_data = defaultdict(lambda: {'amount': 0, 'count': 0})
    merchant_data = defaultdict(lambda: {'amount': 0, 'count': 0, 'category': 'unknown'})
    
    for txn in debit_txns:
        category = txn.get('category', 'other')
        amount = abs(txn.get('amount', 0))
        description = txn.get('description', '')
        
        # Skip investment/savings transactions (not spending)
        if category in ['investment', 'emi', 'insurance']:
            continue
        
        category_data[category]['amount'] += amount
        category_data[category]['count'] += 1
        
        # Extract merchant name (simple heuristic)
        merchant = description.split('-')[0].strip() if '-' in description else description
        if merchant and amount > 100:  # Only track meaningful amounts
            merchant_data[merchant]['amount'] += amount
            merchant_data[merchant]['count'] += 1
            merchant_data[merchant]['category'] = category
    
    # Total spending
    total_spent = sum(data['amount'] for data in category_data.values())
    
    # Build category list
    categories = []
    for cat, data in category_data.items():
        categories.append({
            'category': cat,
            'amount': data['amount'],
            'percent': round((data['amount'] / total_spent * 100) if total_spent > 0 else 0, 1),
            'transaction_count': data['count']
        })
    
    # Sort by amount
    categories.sort(key=lambda x: x['amount'], reverse=True)
    
    # Top merchants
    merchants = []
    for merchant, data in merchant_data.items():
        merchants.append({
            'name': merchant,
            'amount': data['amount'],
            'transaction_count': data['count'],
            'category': data['category']
        })
    
    merchants.sort(key=lambda x: x['amount'], reverse=True)
    
    # Simple trend analysis (compare top categories to average)
    avg_category_spend = total_spent / len(categories) if categories else 0
    trends = []
    
    for cat_data in categories[:5]:  # Top 5 categories
        amount = cat_data['amount']
        if amount > avg_category_spend * 1.5:
            trends.append({
                'category': cat_data['category'],
                'current_amount': amount,
                'trend': 'high',
                'alert': f"Above average spending"
            })
    
    return {
        'total_spent': total_spent,
        'categories': categories,
        'merchants': merchants[:10],  # Top 10
        'trends': trends
    }


def build_spending_prompt(profile: dict, analysis: Dict) -> str:
    """
    Build prompt for LLM to generate spending insights.
    
    Args:
        profile: Customer profile
        analysis: Spending analysis from Python
        
    Returns:
        Formatted prompt
    """
    financial = profile.get('financial_summary', {})
    
    prompt = f"""You are a financial advisor for IDBI Bank. Analyze this customer's spending patterns and provide insights.

Customer Profile:
- Name: {profile.get('name')}
- Age: {profile.get('age')}
- Monthly Income: ₹{financial.get('monthly_income'):,}
- Monthly Expenses: ₹{financial.get('monthly_expenses'):,}

Spending Analysis:
- Total Spent (recent): ₹{analysis['total_spent']:,}
- Top Categories: {json.dumps(analysis['categories'][:5], indent=2)}
- Top Merchants: {json.dumps(analysis['merchants'][:5], indent=2)}
- High Spending Alerts: {json.dumps(analysis['trends'], indent=2)}

Based on the spending patterns, provide:
1. A summary of their spending behavior
2. 2-3 specific recommendations to optimize spending

Provide response in this EXACT JSON format:
{{
  "summary": "2-3 sentence analysis of spending patterns",
  "recommendations": [
    "Specific recommendation 1 with numbers",
    "Specific recommendation 2 with numbers",
    "Specific recommendation 3 with numbers"
  ]
}}

Guidelines:
- Be specific with amounts and categories
- Suggest realistic optimizations
- Consider their income level
- Positive and constructive tone

ONLY return valid JSON, no markdown formatting."""
    
    return prompt


@router.get("/spending-analysis", response_model=SpendingAnalysisResponse, tags=["AI Endpoints"])
async def get_spending_analysis(
    session_id: str = Query(..., description="Session ID (profile_id)"),
    refresh: bool = Query(False, description="Force refresh cache")
):
    """
    Get detailed spending analysis for the active profile.
    
    This endpoint analyzes transaction history to provide:
    - Spending breakdown by category
    - Top merchants and frequent purchases
    - Spending trends and alerts
    - Recommendations to optimize spending
    
    **No RAG, no tools** - Pure transaction analysis + LLM insights.
    Python categorizes and calculates, LLM provides recommendations.
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
        cached_data = cache.get(profile_id, 'spending_analysis')
        if cached_data:
            response_data = cached_data['data']
            response_data['cached'] = True
            return SpendingAnalysisResponse(**response_data)
    
    # Analyze spending
    analysis = analyze_spending(profile)
    
    # Build prompt
    prompt = build_spending_prompt(profile, analysis)
    
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
            max_tokens=800
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
        
        ai_analysis = json.loads(llm_response)
        
        # Build response
        response_data = {
            "summary": ai_analysis.get('summary', ''),
            "total_spent": analysis['total_spent'],
            "spending_by_category": analysis['categories'],
            "trends": analysis['trends'],
            "top_merchants": analysis['merchants'],
            "recommendations": ai_analysis.get('recommendations', []),
            "profile_id": profile_id,
            "cached": False
        }
        
        # Cache
        cache.set(profile_id, 'spending_analysis', response_data)
        
        return SpendingAnalysisResponse(**response_data)
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing LLM response: {str(e)}. Response was: {llm_response[:200]}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating spending analysis: {str(e)}"
        )
