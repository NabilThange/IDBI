import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.session_store import session_store
from app.core.cache import cache
from app.core.llm_client import llm_client
from app.rag.retriever_bm25 import bm25_retriever
from app.core.mining import analyze_spending_pattern
from app.core.suitability import check_suitability
from app.core.translator import translator
from app.core.database import db, Lead, AuditLog

router = APIRouter(tags=["AI Endpoints"])

# Dependency to get DB session
def get_db():
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()

class ProductRecommendation(BaseModel):
    """Single product recommendation with suitability details"""
    product_type: str
    product_name: str
    recommended_amount: int
    rationale: str
    key_features: List[str]
    tier: str  # 'A' or 'B'
    requires_rm_handoff: bool
    suitability_trail: List[str]

class RecommendationsResponse(BaseModel):
    """Investment recommendations response"""
    summary: str
    total_investable: int
    recommendations: List[ProductRecommendation]
    profile_id: str
    cached: bool
    knowledge_sources: List[str]
    preferred_language: str

class LeadCreateRequest(BaseModel):
    product_name: str
    product_type: str
    recommended_amount: int
    suitability_trail: List[str]

@router.get("/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    session_id: str = Query(..., description="Session ID (profile_id)"),
    refresh: bool = Query(False, description="Force refresh cache"),
    db_session: Session = Depends(get_db)
):
    """
    Get AI-powered investment recommendations for the active profile.
    
    This endpoint uses a combination of Data Mining (spending analyzer),
    Suitability Engine (math & regulatory tiering), and RAG (knowledge retrieval).
    It localizes the output into the customer's preferred language.
    """
    # 1. Get active profile
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}. Please select a profile first."
        )
    
    profile_id = profile['profile_id']
    preferred_lang = profile.get('language_preference', 'English')
    
    # Check cache (unless refresh requested)
    if not refresh:
        cached_data = cache.get(profile_id, 'recommendations')
        if cached_data:
            response_data = cached_data['data']
            # Re-localize cached data if language differs
            localized_data = translator.localize_object(response_data, preferred_lang)
            localized_data['cached'] = True
            localized_data['preferred_language'] = preferred_lang
            return RecommendationsResponse(**localized_data)
            
    # Check if RAG is available
    if not bm25_retriever.is_initialized():
        raise HTTPException(
            status_code=503,
            detail="Knowledge base not available. Run RAG initialization."
        )
        
    # 2. Mine spending patterns to compute baseline essential expense/disposable income
    transactions = profile.get('transactions', [])
    spend_analysis = analyze_spending_pattern(profile_id, transactions)
    
    # 3. Retrieve relevant product information from IDBI knowledge base
    # Build query based on risk profile
    risk_category = profile.get('risk_profile', {}).get('risk_category', 'Moderate')
    query = f"investment options interest rates {risk_category.lower()} risk"
    results = bm25_retriever.retrieve(query, top_k=5)
    knowledge_context = bm25_retriever.format_context(results, max_chunks=3)
    sources = list(set([r['source'] for r in results]))
    
    # 4. Generate recommendations using LLM
    financial = profile.get('financial_summary', {})
    monthly_savings = financial.get('monthly_savings', 0)
    current_sips = sum(
        inv.get('monthly_amount', 0) 
        for inv in profile.get('current_investments', []) 
        if inv.get('type') == 'SIP'
    )
    investable_surplus = monthly_savings - current_sips
    
    goals = profile.get('goals', [])
    
    prompt = f"""You are an expert investment advisor for IDBI Bank. Recommend suitable investment products based on customer profile and IDBI's product offerings.

Customer Profile:
- Name: {profile.get('name')}
- Age: {profile.get('age')}
- Occupation: {profile.get('occupation')}
- Risk Category: {risk_category}
- Monthly Income: ₹{financial.get('monthly_income'):,}
- Monthly Savings: ₹{monthly_savings:,}
- Available investable surplus: ₹{investable_surplus:,}/month
- Goals: {json.dumps(goals, indent=2)}

IDBI Product Information:
{knowledge_context}

Based on this, suggest exactly 2-3 specific IDBI investment schemes (e.g. Suvidha Fixed Deposit, Systematic Investment Plan, Sovereign Gold Bond).
Explain why each product is recommended and highlight key interest rates/features.

Response Format (JSON ONLY):
{{
  "summary": "General overview of the suggested strategy",
  "recommendations": [
    {{
      "product_type": "FD/SIP/Gold/etc",
      "product_name": "Exact scheme name from product info",
      "recommended_amount": 5000,
      "rationale": "Direct rationale matching their risk profile and goal",
      "key_features": ["feature 1 from KB", "feature 2"]
    }}
  ]
}}
DO NOT return any explanation or markdown formatting, return raw JSON string only."""
    
    try:
        system_prompt = (
            "You are an expert investment advisor for IDBI Bank. "
            "Always respond with valid JSON only. "
            "Any text inside the JSON that the customer will read (reasoning, description, notes, insights) "
            "must use simple, everyday English — short sentences, no jargon left unexplained, rounded numbers "
            "with a relatable comparison where useful, and a warm tone like a trusted advisor who knows the customer well."
        )
        llm_response = llm_client.chat_with_system(
            system_prompt=system_prompt,
            user_message=prompt,
            temperature=0.4,
            max_tokens=1500
        ).strip()
        
        # Clean response tags if present
        if llm_response.startswith("```json"):
            llm_response = llm_response[7:]
        if llm_response.startswith("```"):
            llm_response = llm_response[3:]
        if llm_response.endswith("```"):
            llm_response = llm_response[:-3]
        llm_response = llm_response.strip()
        
        ai_recommendations = json.loads(llm_response)
        
        # 5. Suitability Validation & Auditing
        final_recommendations = []
        for rec in ai_recommendations.get('recommendations', []):
            prod_name = rec.get('product_name', '')
            
            # Find matching goal if any
            matched_goal = None
            for goal in goals:
                goal_name = goal.get('name') or goal.get('goal_name')
                if goal_name:
                    # Simple check if goal name matches product category or rationale
                    if goal_name.lower() in rec.get('rationale', '').lower() or goal_name.lower() in prod_name.lower():
                        matched_goal = {
                            'goal_name': goal_name,
                            'target_amount': goal.get('target_amount'),
                            'current_savings': goal.get('current_savings', 0),
                            'target_date': goal.get('target_date')
                        }
                        break
            
            # Check suitability
            suit_res = check_suitability(prod_name, profile, spend_analysis, matched_goal)
            
            final_recommendations.append(ProductRecommendation(
                product_type=rec.get('product_type', 'FD'),
                product_name=prod_name,
                recommended_amount=suit_res['recommended_amount'],
                rationale=rec.get('rationale', ''),
                key_features=rec.get('key_features', []),
                tier=suit_res['tier'],
                requires_rm_handoff=suit_res['requires_rm_handoff'],
                suitability_trail=suit_res['suitability_trail']
            ))
            
        # 6. Write Audit Log
        recs_json = [r.dict() for r in final_recommendations]
        audit = AuditLog(
            customer_id=profile_id,
            endpoint="/api/recommendations",
            recommendation=recs_json,
            reasoning=ai_recommendations.get('summary', ''),
            model_version="aimlapi-deepseek-v4-flash"
        )
        db_session.add(audit)
        db_session.commit()
        
        response_data = {
            "summary": ai_recommendations.get('summary', ''),
            "total_investable": investable_surplus,
            "recommendations": [
                {
                    "product_type": r.product_type,
                    "product_name": r.product_name,
                    "recommended_amount": r.recommended_amount,
                    "rationale": r.rationale,
                    "key_features": r.key_features,
                    "tier": r.tier,
                    "requires_rm_handoff": r.requires_rm_handoff,
                    "suitability_trail": r.suitability_trail
                }
                for r in final_recommendations
            ],
            "profile_id": profile_id,
            "cached": False,
            "knowledge_sources": sources,
            "preferred_language": "English"
        }
        
        # Cache raw english response
        cache.set(profile_id, 'recommendations', response_data)
        
        # 7. Apply Multi-Language localization
        localized_data = translator.localize_object(response_data, preferred_lang)
        localized_data['preferred_language'] = preferred_lang
        
        return RecommendationsResponse(**localized_data)
        
    except Exception as e:
        db_session.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating recommendations: {str(e)}"
        )

@router.post("/recommendations/lead", tags=["AI Endpoints"])
def create_recommendation_lead(
    session_id: str, 
    request: LeadCreateRequest, 
    db_session: Session = Depends(get_db)
):
    """
    Create a Relationship Manager lead when a customer selects a Tier B regulated product.
    """
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Session not found")
        
    try:
        # Determine priority score based on credit score, amount, and age
        credit_score = profile.get('credit_bureau_data', {}).get('credit_score', 750)
        priority_score = 50
        if credit_score > 750:
            priority_score += 20
        if request.recommended_amount > 20000:
            priority_score += 20
            
        lead = Lead(
            customer_id=session_id,
            product_name=request.product_name,
            product_type=request.product_type,
            tier='B',
            recommended_amount=request.recommended_amount,
            suitability_trail=request.suitability_trail,
            status='pending',
            priority_score=priority_score,
            assigned_rm=None,
            rm_notes=None
        )
        db_session.add(lead)
        db_session.commit()
        db_session.refresh(lead)
        
        return {
            "status": "success",
            "message": "Lead successfully generated and routed to RM queue.",
            "lead_id": lead.id,
            "priority_score": lead.priority_score
        }
    except Exception as e:
        db_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
