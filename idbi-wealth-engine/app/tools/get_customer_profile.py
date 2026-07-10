"""
Tool: Get Customer Profile
Returns current customer's complete profile data.
"""

import json
from typing import Dict, Any

from app.core.session_store import session_store


# Tool definition for Groq
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_customer_profile",
        "description": "Retrieve the complete profile of the current customer including demographics, financial summary, risk profile, goals, and recent transactions. Use this when you need customer information to answer questions.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


def get_customer_profile() -> Dict[str, Any]:
    """
    Get the current customer's profile from session store.
    
    Returns:
        Dictionary containing full customer profile
        
    Raises:
        ValueError: If no customer session is active
    """
    profile = session_store.get_profile()
    
    if not profile:
        raise ValueError("No customer profile selected. Please select a profile first.")
    
    # Return a copy to prevent modifications
    return {
        "profile_id": profile.get("profile_id"),
        "name": profile.get("name"),
        "age": profile.get("age"),
        "occupation": profile.get("occupation"),
        "location": profile.get("location"),
        "customer_since": profile.get("customer_since"),
        "risk_profile": profile.get("risk_profile"),
        "financial_summary": profile.get("financial_summary", {}),
        "goals": profile.get("goals", []),
        "recent_transactions_count": len(profile.get("transactions", [])),
        # Don't include full transaction list here to save tokens
        # Use get_transactions tool for detailed transaction data
    }
