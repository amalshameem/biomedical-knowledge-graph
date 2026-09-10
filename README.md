# Biomedical Knowledge Graph Extractor

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18%2F19-61DAFB?style=flat&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2+-3178C6?style=flat&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Neo4j](https://img.shields.io/badge/Neo4j-5.18+-008CC1?style=flat&logo=neo4j&logoColor=white)](https://neo4j.com)
[![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com)

**Biomedical Knowledge Graph Extractor** is an end-to-end biomedical information extraction and interactive graph visualization platform. It parses unstructured documents such as PDFs and extracts named entities with zero-shot biomedical NER, extracts relationship triples with evidence sentences using LLMs, canonicalizes entities via clinical ontologies, enriches relationships with NCBI PubMed citations, and visualizes the resulting knowledge graph using interactive Cytoscape network views.

---

## Architecture & Pipeline

```
  ┌─────────────────────────────────────────────────────────────┐
  │ 1. Document Ingestion                                       │
  │    PDF Upload ──► IBM Docling ──►                           │
  │    Filtering ──► Hierarchical Chunking                      │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
  ┌──────────────────────────────▼──────────────────────────────┐
  │ 2. Dual Extraction Engine                                   │
  │    Parallel Processing:                                     │
  │    ├─► GLiNER NER (35 Biomedical Labels: Genes, Drugs, ...) │
  │    └─► LLM Triple Extraction                                │
  │        (e.g., treats, causes, interacts_with, inhibits)     │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
  ┌──────────────────────────────▼──────────────────────────────┐
  │ 3. Normalization                                            │
  │    Entity normalization ──►                                 │ 
  │     Clinical Dictionaries & Matching                        │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
  ┌──────────────────────────────▼──────────────────────────────┐
  │ 4. NCBI PubMed Citation Enrichment                          │
  │    Entrez E-Utilities ──► Automatic PMID Discovery          │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
  ┌──────────────────────────────▼──────────────────────────────┐
  │ 5. Dual-Persistence & Interactive Exploration               │
  │    ├─► Neo4j: Typed graph nodes, colored relations, PMIDs   │
  │    ├─► PostgreSQL / SQLite: Relational projects & metadata  │
  │    └─► React + Cytoscape.js: Knowledge graph visualization  │
  └─────────────────────────────────────────────────────────────┘
```

---

## Key Features

* **Multi-Provider LLM Integration**: Connects to **LM Studio**, **Ollama** (Local & Cloud), **OpenRouter**, **Google Gemini**, **Groq**, **Anthropic**, and **OpenAI**. Dynamic model auto-discovery populates available models on key entry.
* **Evidence Grounding**: Every extracted relationship stores the exact verbatim sentence from the source paper, enabling instant clinical validation.
* **Interactive Cytoscape Visualizer**: Filter graph nodes by entity type (Genes, Diseases, Drugs, etc.), adjust connection degree thresholds, click nodes/edges for full provenance inspect drawers, and run physics layouts (`fcose`, `cola`, `concentric`).
* **Multi-Format Export Bundle**: One-click download of project knowledge graphs as a `.zip` file.

---

## Getting Started

One can run this biomedical knowledge graph pipeline using **Docker Compose** (recommended for production/containers) or **Natively** (recommended for local development).

### Method 1: Docker Compose (Quickest)

Ensure [Docker Desktop](https://www.docker.com/products/docker-desktop/) is installed and running.

1. **Clone the repository and navigate to it**

2. **Start all services**:
   ```bash
   docker compose up --build -d
   ```

3. **Open the applications**:
   * **Frontend Web UI**: [http://localhost:5173](http://localhost:5173)
   * **FastAPI Backend Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   * **Neo4j Browser**: [http://localhost:7474](http://localhost:7474) *(User: `neo4j` | Password: `password`)*
   * **PostgreSQL Database**: `localhost:5432` *(User: `biomed` | Password: `biomed_password` | DB: `biomed_kg`)*

> [!TIP]
> **Accessing Local Host Models from Docker**:
> To connect to **LM Studio** or **Ollama** running on your host computer from inside the Docker container:
> * LM Studio: `http://host.docker.internal:1234/v1`
> * Local Ollama: `http://host.docker.internal:11434`

To shut down:
```bash
docker compose down
```

---

### Method 2: Native Local Development

#### Prerequisites
* Python 3.10+ (`python3 --version`)
* Node.js 18+ or 20+ (`node -v`)
* Neo4j (via Docker or [Neo4j Desktop](https://neo4j.com/download/))

#### Step 1: Start Neo4j
```bash
docker run -d \
  --name biomed_neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -e NEO4J_PLUGINS='["apoc"]' \
  neo4j:5.18.0-community
```

#### Step 2: Start the Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Run backend (uses zero-config SQLite by default)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Step 3: Start the Frontend
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Navigate to [http://localhost:5173](http://localhost:5173).

---

## Supported LLM Providers

| Provider | Endpoint | Cost / Setup |
| :--- | :--- | :--- |
| **LM Studio** | `http://localhost:1234/v1` | **Free & Offline** (Runs directly on your Mac/PC) |
| **Ollama Local** | `http://localhost:11434` | **Free & Offline** (Runs local GGUF models) |
| **Ollama Cloud** | `https://ollama.com/v1` | **Free Starter Tier** (`gpt-oss:20b`, `nemotron-3-nano:30b`) |
| **Google Gemini** | `https://generativelanguage.googleapis.com` | **Free Tier** via [Google AI Studio](https://aistudio.google.com) (`gemini-2.0-flash`) |
| **Groq** | `https://api.groq.com/openai/v1` | **Free Tier** via [Groq Console](https://console.groq.com) (`llama-3.3-70b-versatile`) |
| **OpenRouter** | `https://openrouter.ai/api/v1` | 100+ multi-provider LLMs |
| **Anthropic / OpenAI** | Official endpoints | Commercial API keys (Claude 3.5, GPT-4o) |

---

## Project Structure

```
BioKG/
├── .env.example              # Sample environment variables
├── .gitignore                # Production gitignore for Python, Node, & SQLite
├── .dockerignore             # Exclusions for clean Docker builds
├── docker-compose.yml        # Orchestration for Neo4j, Postgres, Backend, Frontend
├── README.md                 # Project documentation
├── run_dev.sh                # 1-click startup script for local development
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py           # FastAPI entrypoint & CORS
│   │   ├── api/v1/           # REST endpoints (projects, extraction, graph, export, llm, settings)
│   │   ├── core/             # Configuration & DB connection management
│   │   ├── models/           # SQLAlchemy schemas & Pydantic domain models
│   │   └── services/         # Extraction pipeline, GLiNER NER, LLM, Normalizer, Neo4j, PubMed
│   └── tests/                # Automated pytest test suites
└── frontend/
    ├── Dockerfile
    ├── nginx.conf            # Nginx proxy & SSE streaming configuration
    ├── package.json
    ├── vite.config.ts
    ├── index.html
    └── src/
        ├── App.tsx           # Primary application router
        ├── components/       # Hub, Extraction progress, Cytoscape graph, Node inspector, Export
        └── services/api.ts   # Axios API client
```

---

## License

This project is licensed under the [MIT LICENSE](LICENSE).
