import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load main env file to get environment name
load_dotenv('.env')
env = os.getenv('ENV', 'local')


class Settings(BaseSettings):
    # 環境設定
    ENV: str = "local"

    # 專案設定
    PROJECT_NAME: str = "Otterra Travel"
    API_PREFIX: str = "/api"
    ALLOWED_ORIGINS: list = ["http://localhost:3000"]
    DEBUG: bool = True

    # OAuth Setting
    GOOGLE_CLIENT_ID: str = ""

    # JWT 設定
    JWT_SECRET: str = "053a8db4c6f22105b5e0e8bc705a06bd2b882d3b60f2e180b85a61cb7cce0d3488db7eee919934146d3a003787cf3adef81a763870eb889c040cf790334f5a5519c88ee408c8c1487c1af5371110c2c1b43739e6eb5fb4d4a95945e1b623c45e8d09f94d8b987445684591ea9b1d8a81613e5759387595126ac8f5371f34297c"
    JWT_EXPIRATION_SECONDS: int = 86400
    JWT_REFRESH_EXPIRATION_SECONDS: int = 604800

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    # Redis
    REDIS_ENABLED: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    # AI/LLM features - switch provider via LLM_PROVIDER in .env, no code change needed
    LLM_PROVIDER: str = "openrouter"  # openrouter | gemini | groq | openai | ollama
    LLM_MODEL: str = "google/gemini-2.0-flash" 
    OPENROUTER_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_THINKING_BUDGET: int = -1  # -1 = dynamic, 0 = off, 1-24576 = fixed
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    TAVILY_API_KEY: str = ""                # RAG web search key


    class Config:
        # 根據 .env 中的 ENV 值載入對應的配置檔
        env_file = f"config/.env.{env}"
        case_sensitive = True

settings = Settings()
