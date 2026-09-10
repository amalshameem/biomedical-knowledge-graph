import os
import platform
from pathlib import Path
from pydantic_settings import BaseSettings

os.environ.setdefault("DOCLING_DEVICE", "cpu")
os.environ.setdefault("OMP_NUM_THREADS", "4")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = BASE_DIR / "app" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Biomedical Knowledge Graph API"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    
    # SQLite / Postgres Database (forward slashes required for Windows SQLite URIs)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{str(BASE_DIR / 'biomed.db').replace(chr(92), '/')}")
    
    # Neo4j Database
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    # Default External Providers
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")
    ENTREZ_EMAIL: str = os.getenv("ENTREZ_EMAIL", "bot@example.com")
    ENTREZ_API_KEY: str = os.getenv("ENTREZ_API_KEY", "")
    
    model_config = {
        "env_file": (
            str(BASE_DIR.parent / ".env"),  # Root .env
            str(BASE_DIR / ".env"),         # backend/.env
            ".env"
        ),
        "extra": "ignore"
    }

settings = Settings()
