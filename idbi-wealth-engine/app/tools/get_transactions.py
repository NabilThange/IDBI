"""
Tool: Get Transactions
Returns customer's transaction history with optional filtering.
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.session_store import session_store


# Tool definition for Groq
TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "get_transactions",
        "description": "Retrieve customer's transaction history. Can filter by category (e.g., 'food', 'rent', 'entertainment') or transaction type ('debit' or 'credit'). Returns up to 20 most recent transactions.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "description": "Filter by transaction category (e.g., 'food', 'rent', 'transportation', 'entertainment', 'shopping', 'utilities', 'investment')"
                },
                "transaction_type": {
                    "type": "string",
                    "enum": ["debit", "credit"],
                    "description": "Filter by transaction type: 'debit' for expenses, 'credit' for income"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of transactions to return (default: 20, max: 50)"
                }
            },
            "required": []
        }
    }
}


def get_transactions(
    category: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Get customer's transaction history with optional filtering.
    
    Args:
        category: Filter by transaction category (case-insensitive)
        transaction_type: Filter by 'debit' or 'credit'
        limit: Maximum number of transactions to return
        
    Returns:
        Dictionary containing filtered transactions and summary
        
    Raises:
        ValueError: If no customer session is active
    """
    profile = session_store.get_profile()
    
    if not profile:
        raise ValueError("No customer profile selected. Please select a profile first.")
    
    transactions = profile.get("transactions", [])
    
    # Apply filters
    filtered = transactions
    
    if category:
        category_lower = category.lower()
        filtered = [t for t in filtered if t.get("category", "").lower() == category_lower]
    
    if transaction_type:
        filtered = [t for t in filtered if t.get("type", "").lower() == transaction_type.lower()]
    
    # Sort by date (most recent first)
    filtered.sort(key=lambda t: t.get("date", ""), reverse=True)
    
    # Apply limit
    limit = min(max(1, limit), 50)  # Clamp between 1 and 50
    filtered = filtered[:limit]
    
    # Calculate summary
    total_amount = sum(t.get("amount", 0) for t in filtered)
    debit_count = sum(1 for t in filtered if t.get("type") == "debit")
    credit_count = sum(1 for t in filtered if t.get("type") == "credit")
    
    return {
        "transactions": filtered,
        "count": len(filtered),
        "total_amount": total_amount,
        "debit_count": debit_count,
        "credit_count": credit_count,
        "filters_applied": {
            "category": category,
            "transaction_type": transaction_type,
            "limit": limit
        }
    }
