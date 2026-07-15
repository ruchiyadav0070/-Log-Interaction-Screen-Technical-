import os
from dotenv import load_dotenv

load_dotenv()

# Database Config
# If MySQL or Postgres URL is provided, it will use that, otherwise falls back to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm.db")

# Groq API Config
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Server Config
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# LLM Models
GEMMA_MODEL = "gemma2-9b-it"
LLAMA_MODEL = "llama-3.3-70b-versatile"
