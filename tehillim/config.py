import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    HOST = os.environ.get("HOST", "127.0.0.1")
    PORT = int(os.environ.get("PORT", 8000))
    DEBUG = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
