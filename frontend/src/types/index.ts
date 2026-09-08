export interface DocumentInfo {
  id: string;
  filename: string;
  file_size: number;
  chunks_count: number;
  created_at: string;
}

export interface TripleItem {
  id?: string;
  entity1: string;
  entity1_type: string;
  relationship: string;
  entity2: string;
  entity2_type: string;
  evidence: string;
  pubmed_ids: string;
}

export interface Project {
  id: string;
  name: string;
  description?: string;
  status: 'created' | 'processing' | 'completed' | 'failed';
  provider?: string;
  model?: string;
  total_chunks: number;
  total_triples: number;
  execution_time: number;
  created_at: string;
  updated_at: string;
  documents_count: number;
  documents?: DocumentInfo[];
  triples?: TripleItem[];
}

export interface ExtractionProgressEvent {
  project_id: string;
  stage: 'docling' | 'ner_gliner' | 'llm_triples' | 'normalizer' | 'pubmed' | 'neo4j' | 'completed' | 'error';
  progress: number;
  message: string;
  current_chunk: number;
  total_chunks: number;
  triples_found: number;
  timestamp: number;
}

export interface CytoscapeNodeData {
  id: string;
  label: string;
  type: string;
  category?: string;
  sub_category?: string;
  color: string;
  degree: number;
  canonical_name?: string;
}

export interface CytoscapeEdgeData {
  id: string;
  source: string;
  target: string;
  label: string;
  relationship: string;
  color?: string;
  evidence: string;
  pubmed_ids: string;
}

export interface CytoscapeGraphData {
  elements: {
    nodes: Array<{ data: CytoscapeNodeData }>;
    edges: Array<{ data: CytoscapeEdgeData }>;
  };
  stats: {
    total_nodes: number;
    total_edges: number;
    types_count: Record<string, number>;
    categories_count?: Record<string, number>;
    subcategories_count?: Record<string, number>;
  };
}

export interface GlobalSettings {
  default_provider?: string;
  openrouter_api_key?: string;
  ollama_endpoint?: string;
  ollama_api_key?: string;
  lmstudio_endpoint?: string;
  anthropic_api_key?: string;
  gemini_api_key?: string;
  openai_api_key?: string;
  openai_endpoint?: string;
  groq_api_key?: string;
  mistral_api_key?: string;
  entrez_email?: string;
  entrez_api_key?: string;
  neo4j_uri?: string;
  neo4j_user?: string;
  neo4j_password?: string;
}

export interface LLMProvider {
  name: string;
  default_endpoint: string;
  requires_key: boolean;
  description?: string;
}
