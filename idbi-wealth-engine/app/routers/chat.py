"""
Agentic Chat Router
Conversational AI with tool calling for dynamic information retrieval.
"""

import json
import time
import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

def get_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

from app.core.session_store import session_store
from app.core.llm_client import llm_client
from app.tools import TOOL_REGISTRY
from app.tools.get_customer_profile import TOOL_DEFINITION as GET_PROFILE_DEF
from app.tools.get_transactions import TOOL_DEFINITION as GET_TRANSACTIONS_DEF
from app.tools.search_idbi_knowledge import TOOL_DEFINITION as SEARCH_KNOWLEDGE_DEF
from app.tools.calculate_goal_projection import TOOL_DEFINITION as CALCULATE_GOAL_DEF
from app.core.database import db, AuditLog
from app.core.translator import translator


router = APIRouter()


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str  # user, assistant, system
    content: str
    sources: Optional[List[dict]] = None
    action: Optional[dict] = None


class ChatRequest(BaseModel):
    """Chat request payload"""
    message: str
    session_id: str
    language: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response"""
    message: str
    sources: Optional[List[dict]] = None  # Source pills [{url, title, category}]
    action: Optional[dict] = None  # CTA button {label, url}
    tool_calls_made: List[dict]
    iterations: int
    session_id: str


class ChatHistoryResponse(BaseModel):
    """Chat history response"""
    messages: List[ChatMessage]
    session_id: str
    count: int


# System prompt for the wealth advisor agent
WEALTH_ADVISOR_SYSTEM_PROMPT = """You are the customer's personal wealth advisor at IDBI Bank. Talk like someone who has known this customer for years and genuinely wants good things for them — not like a call center script.

**HOW TO TALK**
- Use simple, everyday English. Short sentences. One idea at a time.
- Never use banking jargon without explaining it in plain words the first time — e.g. "SIP (a fixed amount you invest every month)", "disposable income (money left after your must-pay expenses)".
- No long paragraphs. 2-4 short sentences per point is enough. Add more only if the customer asks for more detail.
- Round off numbers and make them relatable. Say "about ₹15,000" not "₹15,247.83". Where it helps, compare to something familiar: "that's roughly one month's rent."
- Some customers are very comfortable with English (NRIs, business owners) and some are not. Keep the same simple, clear style for everyone — it works for both, and it never feels condescending.
- Structure every answer the same way: give the direct answer first, then a short reason, then one simple next step. Don't make the customer wait through setup before getting to the point.
- Warm, not clinical. Encourage, don't lecture.

**YOUR CAPABILITIES**
- Look up the customer's profile (age, income, risk profile, goals)
- Look up their transaction and spending history
- Search IDBI's product knowledge base for rates, eligibility, and features
- Calculate goal projections (e.g. "can I afford a house in 3 years?")

**HOW TO USE YOUR TOOLS**
1. If you don't already know who you're talking to, check their profile first.
2. Never guess a product detail or rate — always search the knowledge base for it.
3. Never do goal math in your head — always use the goal projection tool.
4. When talking about their spending, pull real transaction data, don't assume.
5. Weave tool results into natural sentences. Never say "let me use a tool" or mention tool names to the customer.

**WHEN RECOMMENDING PRODUCTS OR ACTIONS**
- When you find a product that fits the customer's needs, recommend it directly and explain why it suits them.
- If the knowledge base includes an application link or product page, mention the product naturally — the system will automatically show an "Apply Now" or relevant action button below your message.
- Don't ask "would you like a link?" or "should I provide the application form?" — just give your recommendation. The button will appear when relevant.
- Keep your explanation focused on why it's right for them, not on how to apply (the button handles that).

**EXAMPLES**
- "What are FD rates?" → search the knowledge base, then answer simply: "Right now, IDBI's Fixed Deposit gives about 6.5% to 7% a year, depending on how long you keep the money in."
- "Can I buy a house in 3 years?" → use the goal tool, then: "You'd need to save about ₹25,000 a month for that. Right now you have about ₹20,000 spare each month, so it's close — a small boost would get you there."
- "Where did my money go last month?" → pull transactions: "Most of it, about ₹35,000, went to rent and groceries. The rest, around ₹8,000, was eating out and shopping."
- "What credit card should I get?" → search knowledge base, then: "The IDBI Aspire Platinum Card is your best fit — no joining fee, you earn points on everyday purchases, and there's a 1% fuel discount. It's designed for middle-class earners like you." (System will show Apply button automatically)

Always double-check with a tool rather than guess. A short pause for an accurate answer beats a fast, wrong one."""


# Tool definitions for Groq
TOOL_DEFINITIONS = [
    GET_PROFILE_DEF,
    GET_TRANSACTIONS_DEF,
    SEARCH_KNOWLEDGE_DEF,
    CALCULATE_GOAL_DEF,
]


@router.post("/chat", response_model=ChatResponse, tags=["AI Endpoints"])
async def chat(request: ChatRequest = Body(...)):
    """
    Agentic chat endpoint with tool calling.
    
    The AI agent can:
    - Call tools dynamically based on the conversation
    - Maintain conversation history
    - Provide personalized financial advice
    - Search IDBI knowledge base
    - Calculate goal projections
    
    **This is the most advanced endpoint** - uses full agentic loop with tools.
    """
    start_time = time.time()
    session_id = request.session_id
    user_message = request.message
    print(f"[{get_timestamp()}] [CHAT] User query: \"{user_message}\" (Session: {session_id})")
    
    # Verify session exists
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}. Please select a profile first."
        )
    
    # Get chat history (limit to last 10 messages to manage context window)
    history = session_store.get_chat_history(session_id, limit=10)
    
    # Build messages for LLM
    messages = [
        {"role": "system", "content": WEALTH_ADVISOR_SYSTEM_PROMPT}
    ]
    
    # Add conversation history (without timestamps)
    for msg in history:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    # Add current user message
    messages.append({
        "role": "user",
        "content": user_message
    })
    
    # Call LLM with tool calling loop
    try:
        result = llm_client.chat_with_tools(
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_registry=TOOL_REGISTRY,
            temperature=0.7,
            max_tokens=2000,
            max_iterations=10
        )
        
        assistant_message = result["content"]
        tool_calls_made = result["tool_calls_made"]
        
        # Extract RAG sources + action if knowledge search was used
        rag_sources = None
        rag_action = None
        for tc in tool_calls_made:
            if tc.get("name") == "search_idbi_knowledge" and tc.get("result"):
                rag_sources = tc["result"].get("sources")
                rag_action = tc["result"].get("action")
                break
        iterations = result["iterations"]
        
    except Exception as e:
        # Log error and return helpful message
        print(f"Error in chat tool calling: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat error: {str(e)}"
        )
    
    # Save to chat history
    session_store.add_chat_message(session_id, "user", user_message)
    session_store.add_chat_message(
        session_id, "assistant", assistant_message, sources=rag_sources, action=rag_action
    )
    
    # Write Audit Log
    db_session = db.get_session()
    try:
        audit = AuditLog(
            customer_id=session_id,
            endpoint="/api/chat",
            recommendation={"user_message": user_message, "tool_calls": tool_calls_made},
            reasoning={"assistant_response": assistant_message},
            model_version="groq-llama-3.1"
        )
        db_session.add(audit)
        db_session.commit()
    except Exception as e:
        print(f"Audit log failed in chat: {e}")
        db_session.rollback()
    finally:
        db_session.close()

    # Translate assistant message if preferred language is not English
    preferred_lang = request.language or profile.get('language_preference', 'English')
    localized_message = assistant_message
    if preferred_lang != 'English':
        localized_message = translator.translate_text(assistant_message, preferred_lang)
    
    duration = time.time() - start_time
    print(f"[{get_timestamp()}] [CHAT] Final response ready in {duration:.3f}s after {iterations} iterations")
    
    return ChatResponse(
        message=localized_message,
        sources=rag_sources,
        action=rag_action,
        tool_calls_made=tool_calls_made,
        iterations=iterations,
        session_id=session_id
    )


@router.get("/chat/history", response_model=ChatHistoryResponse, tags=["AI Endpoints"])
async def get_chat_history(
    session_id: str = Query(..., description="Session ID (profile_id)"),
    limit: Optional[int] = Query(None, description="Limit number of messages returned")
):
    """
    Retrieve chat history for a session.
    
    Useful for:
    - Displaying conversation in UI
    - Debugging agent behavior
    - Exporting conversation logs
    """
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}."
        )
    
    history = session_store.get_chat_history(session_id, limit=limit)
    
    # Remove timestamps for cleaner API response
    messages = [
        ChatMessage(
            role=msg["role"], content=msg["content"],
            sources=msg.get("sources"), action=msg.get("action")
        )
        for msg in history
    ]
    
    return ChatHistoryResponse(
        messages=messages,
        session_id=session_id,
        count=len(messages)
    )


@router.delete("/chat/history", tags=["AI Endpoints"])
async def clear_chat_history(
    session_id: str = Query(..., description="Session ID (profile_id)")
):
    """
    Clear chat history for a session.
    
    Useful for:
    - Starting a fresh conversation
    - Resetting context window
    - Privacy/cleanup
    """
    profile = session_store.get_active_profile(session_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"No active session found for {session_id}."
        )
    
    session_store.clear_chat_history(session_id)
    
    return {
        "status": "success",
        "message": f"Chat history cleared for session {session_id}"
    }
