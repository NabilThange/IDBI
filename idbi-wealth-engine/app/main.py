"""
IDBI AI Wealth Engine - Main FastAPI Application
API-first AI platform for personalized wealth advisory.
"""

import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import APP_NAME, APP_VERSION, DEBUG
from app.core.auth import require_api_key

# Initialize FastAPI app
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="AI-powered wealth management and advisory platform for IDBI Bank",
    debug=DEBUG
)

# CORS Configuration - Allow configured frontend origins only.
# ALLOWED_ORIGINS is a comma-separated list of frontend URLs (e.g. the Vercel URL).
# If unset, the list is empty and no cross-origin requests are permitted.
_allowed = os.getenv("ALLOWED_ORIGINS", "")
allow_origins = [o.strip() for o in _allowed.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health Check Endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint - API status check"""
    return {
        "status": "operational",
        "service": APP_NAME,
        "version": APP_VERSION,
        "message": "IDBI AI Wealth Engine is running"
    }


@app.get("/health", tags=["System"])
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": APP_NAME,
        "version": APP_VERSION,
        "components": {
            "api": "operational",
            "llm": "ready",
            "rag": "ready",   # Will validate after Phase 3
        }
    }


# Mount routers
from app.routers import session, financial_health, recommendations, insights, spending, goals, admin, chat, rm, bank, quiz, voice

@app.on_event("startup")
def startup_event():
    from app.core.database import db
    from app.rag.ingest_crawl4ai import Crawl4AIIngester, has_metadata_index
    db.init_db()
    if not has_metadata_index():
        Crawl4AIIngester().run()

app.include_router(session.router, prefix="/api", tags=["Session"], dependencies=[Depends(require_api_key)])
app.include_router(quiz.router, prefix="/api", tags=["Quiz"], dependencies=[Depends(require_api_key)])
app.include_router(financial_health.router, prefix="/api", tags=["AI Endpoints"], dependencies=[Depends(require_api_key)])
app.include_router(recommendations.router, prefix="/api", tags=["AI Endpoints"], dependencies=[Depends(require_api_key)])
app.include_router(insights.router, prefix="/api", tags=["AI Endpoints"], dependencies=[Depends(require_api_key)])
app.include_router(spending.router, prefix="/api", tags=["AI Endpoints"], dependencies=[Depends(require_api_key)])
app.include_router(goals.router, prefix="/api", tags=["AI Endpoints"], dependencies=[Depends(require_api_key)])
app.include_router(chat.router, prefix="/api", tags=["AI Endpoints - Agentic"], dependencies=[Depends(require_api_key)])
app.include_router(voice.router, prefix="/api", tags=["Voice AI"], dependencies=[Depends(require_api_key)])
app.include_router(rm.router, prefix="/api", tags=["Relationship Manager"], dependencies=[Depends(require_api_key)])
app.include_router(bank.router, prefix="/api", tags=["Bank Intelligence"], dependencies=[Depends(require_api_key)])
app.include_router(admin.router, prefix="/api", tags=["Admin"], dependencies=[Depends(require_api_key)])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=DEBUG
    )
