"""
Admin Router
Provides endpoints for managing rules, cache, and system configuration.
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.rules_engine import rules_engine
from app.core.cache import cache

router = APIRouter()


class RulesInfoResponse(BaseModel):
    """Rules configuration information"""
    version: str
    last_updated: str
    description: str
    rules_file: str
    components: int


@router.get("/admin/rules/info", response_model=RulesInfoResponse, tags=["Admin"])
async def get_rules_info():
    """
    Get information about the currently loaded scoring rules.
    Shows version, last update date, and number of components.
    """
    info = rules_engine.get_rules_info()
    return RulesInfoResponse(**info)


@router.get("/admin/rules/full", tags=["Admin"])
async def get_full_rules():
    """
    Get the complete rules configuration.
    Useful for auditing scoring logic and thresholds.
    """
    return {
        "rules": rules_engine.rules,
        "info": rules_engine.get_rules_info()
    }


@router.get("/admin/rules/thresholds", tags=["Admin"])
async def get_thresholds():
    """
    Get configured thresholds for financial health metrics.
    Shows targets for savings ratio, emergency fund, debt levels, etc.
    """
    return {
        "thresholds": rules_engine.get_thresholds(),
        "version": rules_engine.get_rules_version()
    }


@router.get("/admin/rules/grading", tags=["Admin"])
async def get_grading_scale():
    """
    Get the score-to-grade mapping.
    Shows how numeric scores (0-100) map to letter grades (A+, A, B+, etc.).
    """
    return {
        "grading": rules_engine.rules.get('grading', {}),
        "version": rules_engine.get_rules_version()
    }


@router.post("/admin/rules/reload", tags=["Admin"])
async def reload_rules():
    """
    Reload rules from the configuration file.
    Use this after updating financial_health_rules.json to apply changes
    without restarting the server.
    """
    try:
        rules_engine.reload_rules()
        return {
            "status": "success",
            "message": "Rules reloaded successfully",
            "info": rules_engine.get_rules_info()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to reload rules: {str(e)}"
        }


@router.delete("/admin/cache/clear/{profile_id}", tags=["Admin"])
async def clear_profile_cache(profile_id: str, endpoint: str = None):
    """
    Clear cached AI responses for a specific profile.
    
    Args:
        profile_id: Customer profile identifier
        endpoint: Optional specific endpoint to clear (if None, clears all)
    """
    try:
        cache.invalidate(profile_id, endpoint)
        return {
            "status": "success",
            "message": f"Cache cleared for profile {profile_id}" + (f" endpoint {endpoint}" if endpoint else ""),
            "profile_id": profile_id,
            "endpoint": endpoint
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/admin/system/info", tags=["Admin"])
async def get_system_info():
    """
    Get system information and configuration.
    """
    from app.config import AIMLAPI_MODEL, APP_NAME, APP_VERSION, EMBEDDING_MODEL, DEBUG
    from app.core.llm_client import llm_client
    
    return {
        "application": {
            "name": APP_NAME,
            "version": APP_VERSION,
            "debug_mode": DEBUG
        },
        "llm": {
            "provider": "AIMLAPI",
            "model": AIMLAPI_MODEL,
            "info": llm_client.get_usage_info()
        },
        "rag": {
            "embedding_model": EMBEDDING_MODEL,
            "status": "not_initialized"  # Will update in Phase 3
        },
        "rules": rules_engine.get_rules_info()
    }
