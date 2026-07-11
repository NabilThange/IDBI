"""
Configuration management for IDBI AI Wealth Engine.
Loads environment variables and provides centralized config access.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
PROFILES_DIR = BASE_DIR / "profiles"
KB_DIR = BASE_DIR / "kb"
CACHE_DIR = BASE_DIR / "cache"
RAG_INDEX_DIR = BASE_DIR / "rag" / "index"

# Ensure necessary directories exist
PROFILES_DIR.mkdir(exist_ok=True)
KB_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
RAG_INDEX_DIR.mkdir(parents=True, exist_ok=True)

# API Configuration
AIMLAPI_API_KEY = os.getenv("AIMLAPI_API_KEY", "")
if not AIMLAPI_API_KEY:
    print("⚠️  WARNING: AIMLAPI_API_KEY not set in environment variables")

# Model Configuration
AIMLAPI_MODEL = os.getenv("AIMLAPI_MODEL", "deepseek/deepseek-v4-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")

# Application Settings
APP_NAME = os.getenv("APP_NAME", "IDBI AI Wealth Engine")
APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# LLM Settings
MAX_TOKENS = 2048
TEMPERATURE = 0.7

# RAG Settings
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOP_K_RETRIEVAL = 5
RERANK_TOP_N = 3

# Cache Settings
CACHE_ENABLED = True
