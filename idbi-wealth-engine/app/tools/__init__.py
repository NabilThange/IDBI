"""
Tools for AI Agent Tool Calling
Each tool is a wrapper around existing logic, exposing it for agentic chat.
"""

from .get_customer_profile import get_customer_profile
from .get_transactions import get_transactions
from .search_idbi_knowledge import search_idbi_knowledge
from .calculate_goal_projection import calculate_goal_projection


# Tool registry for the LLM client
TOOL_REGISTRY = {
    "get_customer_profile": get_customer_profile,
    "get_transactions": get_transactions,
    "search_idbi_knowledge": search_idbi_knowledge,
    "calculate_goal_projection": calculate_goal_projection,
}


__all__ = [
    "get_customer_profile",
    "get_transactions",
    "search_idbi_knowledge",
    "calculate_goal_projection",
    "TOOL_REGISTRY",
]
