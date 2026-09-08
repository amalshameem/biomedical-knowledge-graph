import os
from typing import List
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.sql_models import GlobalSetting
from app.models.domain import LLMProviderInfo
from app.services.llm_service import fetch_models

router = APIRouter()

PROVIDERS = [
    LLMProviderInfo(name="Ollama", default_endpoint="http://localhost:11434", requires_key=False, description="Local or Cloud Ollama instance"),
    LLMProviderInfo(name="LM Studio", default_endpoint="http://localhost:1234/v1", requires_key=False, description="Local OpenAI-compatible inference"),
    LLMProviderInfo(name="OpenRouter", default_endpoint="https://openrouter.ai/api/v1", requires_key=True, description="Multi-provider LLM gateway"),
    LLMProviderInfo(name="Anthropic", default_endpoint="https://api.anthropic.com/v1", requires_key=True, description="Claude 3.5 Sonnet / Haiku / Opus"),
    LLMProviderInfo(name="Google Gemini", default_endpoint="https://generativelanguage.googleapis.com", requires_key=True, description="Gemini 2.0 Flash & 1.5 Pro"),
    LLMProviderInfo(name="OpenAI", default_endpoint="https://api.openai.com/v1", requires_key=True, description="GPT-4o, GPT-4o-mini, o1, o3-mini"),
    LLMProviderInfo(name="Groq", default_endpoint="https://api.groq.com/openai/v1", requires_key=True, description="Ultra-fast Llama 3.3 & DeepSeek R1"),
    LLMProviderInfo(name="Mistral AI", default_endpoint="https://api.mistral.ai/v1", requires_key=True, description="Mistral Large & Codestral")
]

@router.get("/providers", response_model=List[LLMProviderInfo])
def get_providers():
    return PROVIDERS

@router.get("/models", response_model=List[str])
def get_models(
    provider: str = Query("LM Studio"),
    endpoint: str = Query(""),
    api_key: str = Query(""),
    db: Session = Depends(get_db)
):
    # Lookup saved settings if api_key or endpoint are empty
    if not api_key or not endpoint:
        try:
            db_settings = {s.key: s.value for s in db.query(GlobalSetting).all()}
        except Exception:
            db_settings = {}
            
        prov_lower = provider.lower().replace(" ", "").replace("ai", "")

        if not api_key:
            if "ollama" in prov_lower:
                api_key = db_settings.get("ollama_api_key") or os.getenv("OLLAMA_API_KEY", "")
            elif "openrouter" in prov_lower:
                api_key = db_settings.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY", "")
            elif "anthropic" in prov_lower:
                api_key = db_settings.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY", "")
            elif "gemini" in prov_lower or "google" in prov_lower:
                api_key = db_settings.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
            elif "openai" in prov_lower:
                api_key = db_settings.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")
            elif "groq" in prov_lower:
                api_key = db_settings.get("groq_api_key") or os.getenv("GROQ_API_KEY", "")
            elif "mistral" in prov_lower:
                api_key = db_settings.get("mistral_api_key") or os.getenv("MISTRAL_API_KEY", "")

        if not endpoint:
            if "ollama" in prov_lower:
                endpoint = db_settings.get("ollama_endpoint", "")
            elif "lmstudio" in prov_lower:
                endpoint = db_settings.get("lmstudio_endpoint", "")
            elif "openai" in prov_lower:
                endpoint = db_settings.get("openai_endpoint", "")

    models = fetch_models(provider=provider, endpoint=endpoint, api_key=api_key)
    return models
