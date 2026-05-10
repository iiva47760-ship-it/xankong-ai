import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

AI_PROVIDERS = {
    "gemini": {
        "api_key": os.getenv("GEMINI_KEY", ""),
        "model": "gemini-1.5-flash",
        "enabled": bool(os.getenv("GEMINI_KEY")),
    },
    "openai": {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "gpt-4-turbo-preview",
        "enabled": bool(os.getenv("OPENAI_API_KEY")),
    },
}

DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "gemini")

NEWS_API_KEY    = os.getenv("NEWS_API_KEY", "")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
CRYPTO_API_KEY  = os.getenv("CRYPTO_API_KEY", "")
ALPHA_VANTAGE_KEY     = os.getenv("ALPHA_VANTAGE_KEY", "")
TWITTER_BEARER_TOKEN  = os.getenv("TWITTER_BEARER_TOKEN", "")

API_HOST  = os.getenv("API_HOST", "0.0.0.0")
API_PORT  = int(os.getenv("PORT", os.getenv("API_PORT", "8888")))
API_DEBUG = os.getenv("API_DEBUG", "False").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")

CACHE_TTL = int(os.getenv("CACHE_TTL", "3600"))
