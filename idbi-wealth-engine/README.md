# IDBI AI Wealth Engine

**AI-powered Digital Wealth Management Platform for IDBI Bank**

An API-first AI platform that integrates into IDBI Bank's mobile application to deliver personalized, scalable wealth advisory services through an intuitive digital interface.

## 🎯 Project Overview

This is a submission for **IDBI Innovate 2026 - Track 01: Digital Wealth Management**

The AI Wealth Engine is NOT a standalone chatbot or banking app. It's an intelligent layer that enhances the existing IDBI Bank mobile application with:

- **Personalized Financial Insights** - AI-powered analysis of spending, savings, and investments
- **Smart Recommendations** - Context-aware product suggestions (SIP, FD, Mutual Funds, etc.)
- **Goal Planning** - AI-assisted financial goal tracking and projections
- **Conversational AI** - Natural language financial advisory
- **Spending Analysis** - Transaction categorization and trend detection
- **Financial Health Score** - Comprehensive wellness assessment

## 🏗️ Tech Stack

- **Backend:** FastAPI (async, API-first)
- **LLM:** Groq (llama-3.1 models with tool-calling)
- **Embeddings:** bge-small-en-v1.5 (lightweight, CPU-friendly)
- **Vector Store:** Chroma (embedded mode)
- **Hybrid Search:** BM25 + Vector Search with Reciprocal Rank Fusion
- **Reranker:** FlashRank (CPU-optimized)
- **Data Layer:** JSON files (demo profiles + cached responses)

## 📦 Installation

### 1. Clone or download this repository

### 2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
# Copy the example file
copy .env.example .env

# Edit .env and add your Groq API key
# Get your free API key from: https://console.groq.com/keys
```

### 5. Run the application

```bash
# Development mode with auto-reload
python app/main.py

# Or using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Test the API

Open your browser and visit:
- API Root: http://localhost:8000
- Health Check: http://localhost:8000/health
- Interactive API Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## 🚀 Build Phases

### ✅ Phase 0: Skeleton (Current)
- [x] FastAPI app with health check
- [x] Configuration management
- [x] Basic folder structure

### Phase 1: Demo Profiles
- [ ] Create 4 demo customer profiles
- [ ] Session management endpoints

### Phase 2: First AI Endpoint
- [ ] Financial health score endpoint
- [ ] Groq LLM integration
- [ ] Cache implementation

### Phase 3: RAG Pipeline
- [ ] Knowledge base ingestion
- [ ] Hybrid search (BM25 + Vector)
- [ ] Reranking with FlashRank

### Phase 4: Remaining Endpoints
- [ ] Wealth insights
- [ ] Recommendations
- [ ] Spending analysis
- [ ] Goal progress tracking

### Phase 5: Agentic Chat
- [ ] Tool implementations
- [ ] Tool-calling loop
- [ ] Chat endpoint with history

### Phase 6: Polish
- [ ] Frontend integration
- [ ] Cache busting
- [ ] Quality evaluation

## 📁 Project Structure

```
idbi-wealth-engine/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── config.py            # Configuration management
│   ├── profiles/            # Demo customer profiles (JSON)
│   ├── kb/                  # IDBI knowledge base (markdown files)
│   ├── routers/             # API endpoints
│   ├── core/                # Core services (LLM, session, cache)
│   ├── rag/                 # RAG pipeline (ingest, retrieval)
│   ├── tools/               # LLM tools for agentic behavior
│   └── cache/               # Generated AI responses
├── frontend/                # Minimal demo UI
├── requirements.txt
├── .env                     # Environment variables (create from .env.example)
└── README.md
```

## 🎯 Core Design Principles

- **Python does the math, LLM does the narration** - Never let LLM compute numbers
- **No tools, no RAG** - For endpoints with available data (health, insights)
- **RAG only** - When LLM needs IDBI product knowledge (recommendations)
- **Tools only** - When LLM decides what it needs dynamically (chat)

## 📚 API Endpoints (Planned)

### Session Management
- `GET /profiles` - List available demo profiles
- `POST /session/select` - Select active profile

### AI Endpoints
- `GET /financial-health` - Financial wellness score
- `GET /wealth-insights` - Personalized insights
- `GET /recommendations` - Investment recommendations
- `GET /spending-analysis` - Transaction analysis
- `GET /goal-progress` - Goal tracking
- `POST /chat` - Conversational AI advisor

## 🔑 Environment Variables

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-70b-versatile
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
APP_NAME=IDBI AI Wealth Engine
APP_VERSION=1.0.0
DEBUG=True
```

## 🎪 Features

1. **AI Dashboard** - Personalized financial insights
2. **AI Insights** - Contextual recommendations throughout app
3. **Investment Recommendations** - SIP, FD, Gold, Bonds, Mutual Funds
4. **Goal Planner** - House, Car, Retirement, Emergency Fund, Education
5. **Spending Analyzer** - Transaction categorization & trends
6. **Financial Health Score** - Comprehensive wellness calculation
7. **AI Chat** - Conversational financial advisor
8. **Proactive Notifications** - Smart alerts and recommendations

## 📝 License

Built for IDBI Innovate 2026 Hackathon

## 🙏 Acknowledgments

- IDBI Bank for the hackathon opportunity
- Groq for fast LLM inference
- Open source AI/ML community
