import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.models.sql_models import GlobalSetting
from app.models.domain import SettingsPayload

router = APIRouter()

@router.get("", response_model=SettingsPayload)
def get_global_settings(db: Session = Depends(get_db)):
    db_settings = {s.key: s.value for s in db.query(GlobalSetting).all()}
    return SettingsPayload(
        default_provider=db_settings.get("default_provider", "Ollama"),
        openrouter_api_key=db_settings.get("openrouter_api_key", settings.OPENROUTER_API_KEY),
        ollama_endpoint=db_settings.get("ollama_endpoint", "http://localhost:11434"),
        ollama_api_key=db_settings.get("ollama_api_key", settings.OLLAMA_API_KEY),
        lmstudio_endpoint=db_settings.get("lmstudio_endpoint", "http://localhost:1234/v1"),
        anthropic_api_key=db_settings.get("anthropic_api_key", os.getenv("ANTHROPIC_API_KEY", "")),
        gemini_api_key=db_settings.get("gemini_api_key", os.getenv("GEMINI_API_KEY", "")),
        openai_api_key=db_settings.get("openai_api_key", os.getenv("OPENAI_API_KEY", "")),
        openai_endpoint=db_settings.get("openai_endpoint", "https://api.openai.com/v1"),
        groq_api_key=db_settings.get("groq_api_key", os.getenv("GROQ_API_KEY", "")),
        mistral_api_key=db_settings.get("mistral_api_key", os.getenv("MISTRAL_API_KEY", "")),
        entrez_email=db_settings.get("entrez_email", settings.ENTREZ_EMAIL),
        entrez_api_key=db_settings.get("entrez_api_key", settings.ENTREZ_API_KEY),
        neo4j_uri=db_settings.get("neo4j_uri", settings.NEO4J_URI),
        neo4j_user=db_settings.get("neo4j_user", settings.NEO4J_USER),
        neo4j_password=db_settings.get("neo4j_password", settings.NEO4J_PASSWORD)
    )

@router.post("", response_model=SettingsPayload)
def update_global_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    fields = payload.dict(exclude_none=True)
    for k, v in fields.items():
        existing = db.query(GlobalSetting).filter(GlobalSetting.key == k).first()
        if existing:
            existing.value = v
        else:
            db.add(GlobalSetting(key=k, value=v))
    db.commit()
    return get_global_settings(db)
