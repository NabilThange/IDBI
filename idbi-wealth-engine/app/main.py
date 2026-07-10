"""
IDBI AI Wealth Engine - Main FastAPI Application
API-first AI platform for personalized wealth advisory.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import APP_NAME, APP_VERSION, DEBUG

# Initialize FastAPI app
app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="AI-powered wealth management and advisory platform for IDBI Bank",
    debug=DEBUG
)

# CORS Configuration - Allow frontend to access API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly in production
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
            "llm": "ready",  # Will validate Groq connection later
            "rag": "ready",   # Will validate after Phase 3
        }
    }


# Mount routers
from app.routers import session, financial_health, recommendations, insights, spending, goals, admin, chat, rm, bank, quiz, voice

@app.on_event("startup")
def startup_event():
    from app.core.database import db
    db.init_db()

app.include_router(session.router, prefix="/api", tags=["Session"])
app.include_router(quiz.router, prefix="/api", tags=["Quiz"])
app.include_router(financial_health.router, prefix="/api", tags=["AI Endpoints"])
app.include_router(recommendations.router, prefix="/api", tags=["AI Endpoints"])
app.include_router(insights.router, prefix="/api", tags=["AI Endpoints"])
app.include_router(spending.router, prefix="/api", tags=["AI Endpoints"])
app.include_router(goals.router, prefix="/api", tags=["AI Endpoints"])
app.include_router(chat.router, prefix="/api", tags=["AI Endpoints - Agentic"])
app.include_router(voice.router, prefix="/api", tags=["Voice AI"])
app.include_router(rm.router, prefix="/api", tags=["Relationship Manager"])
app.include_router(bank.router, prefix="/api", tags=["Bank Intelligence"])
app.include_router(admin.router, prefix="/api", tags=["Admin"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG
    )
