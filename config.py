"""
Central configuration for The Unofficial Guide pipeline.
Settings live here (not scattered across files) so chunk size, model names, and
paths are changed in one place. The list of sources is separate — see sources.json.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# --- LLM (generation, Stage 5) — free Groq API key from https://console.groq.com ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
LLM_MODEL = "llama-3.3-70b-versatile"

# --- Embeddings (Stage 3) ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# --- Vector store (Stage 3 / 4) ---
CHROMA_PATH = str(BASE_DIR / "chroma_db")
CHROMA_COLLECTION = "unofficial_guide"

# --- Retrieval (Stage 4) ---
N_RESULTS = 5
