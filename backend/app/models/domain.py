from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class TripleItem(BaseModel):
    id: Optional[str] = None
    entity1: str
    entity1_type: str = "Unknown"
    relationship: str
    entity2: str
    entity2_type: str = "Unknown"
    evidence: Optional[str] = ""
    pubmed_ids: Optional[str] = ""

class DocumentInfo(BaseModel):
    id: str
    filename: str
    file_size: int
    chunks_count: int
    created_at: datetime

class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = ""
    ner_mode: Optional[str] = "advanced"

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    id: str
    status: str
    provider: Optional[str] = None
    model: Optional[str] = None
    ner_mode: Optional[str] = "advanced"
    total_chunks: int = 0
    total_triples: int = 0
    execution_time: float = 0.0
    created_at: datetime
    updated_at: datetime
    documents_count: int = 0

    model_config = {"from_attributes": True}

class ProjectDetail(ProjectResponse):
    documents: List[DocumentInfo] = []
    triples: List[TripleItem] = []

class ExtractionRequest(BaseModel):
    provider: str
    endpoint: Optional[str] = ""
    api_key: Optional[str] = ""
    model: str
    ner_mode: Optional[str] = "advanced"

class ExtractionProgressEvent(BaseModel):
    project_id: str
    stage: str  # 'docling', 'ner_gliner', 'llm_triples', 'normalizer', 'pubmed', 'neo4j', 'completed', 'error'
    progress: float  # 0.0 to 1.0
    message: str
    current_chunk: int = 0
    total_chunks: int = 0
    triples_found: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Cytoscape Graph Models
class CytoscapeNodeData(BaseModel):
    id: str
    label: str
    type: str
    color: str
    degree: int = 0
    canonical_name: Optional[str] = None

class CytoscapeNode(BaseModel):
    data: CytoscapeNodeData

class CytoscapeEdgeData(BaseModel):
    id: str
    source: str
    target: str
    label: str
    relationship: str
    evidence: Optional[str] = ""
    pubmed_ids: Optional[str] = ""

class CytoscapeEdge(BaseModel):
    data: CytoscapeEdgeData

class CytoscapeGraph(BaseModel):
    elements: Dict[str, List[Any]]  # {"nodes": [...], "edges": [...]}
    stats: Dict[str, Any]  # {"total_nodes": X, "total_edges": Y, "types_count": {...}}

# Settings Models
class SettingsPayload(BaseModel):
    default_provider: Optional[str] = "Ollama"
    openrouter_api_key: Optional[str] = None
    ollama_endpoint: Optional[str] = None
    ollama_api_key: Optional[str] = None
    lmstudio_endpoint: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    openai_endpoint: Optional[str] = None
    groq_api_key: Optional[str] = None
    mistral_api_key: Optional[str] = None
    entrez_email: Optional[str] = None
    entrez_api_key: Optional[str] = None
    neo4j_uri: Optional[str] = None
    neo4j_user: Optional[str] = None
    neo4j_password: Optional[str] = None

class LLMProviderInfo(BaseModel):
    name: str
    default_endpoint: str
    requires_key: bool
    description: Optional[str] = ""
