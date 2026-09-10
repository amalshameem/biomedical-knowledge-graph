import os
import asyncio
import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.models.sql_models import Project, Document, Chunk, Triple, GlobalSetting
from app.models.domain import ExtractionRequest
from app.services.pdf_service import extract_text_from_pdf, clean_and_defragment_text
from app.services.embedded_cleaner_service import EmbeddedCleanerService
from app.services.ner_service import (
    extract_entities_from_text,
    extract_entities_detailed,
    snap_entity_to_gliner_spans,
    get_best_ner_type,
    get_relationship_color,
    sanitize_entity_name,
    normalize_to_basic_type,
    BLACKLISTED_ENTITIES
)
from app.services.llm_service import extract_triples_and_evidence_llm, normalize_rel, adapt_endpoint_for_docker
from app.services.normalizer_service import normalize_entities_non_llm
from app.services.pubmed_service import fetch_pubmed_ids_for_triple
from app.services.neo4j_service import sync_triples_to_neo4j

logger = logging.getLogger(__name__)
router = APIRouter()

# Global in-memory SSE event queues & latest state per project
project_queues: Dict[str, asyncio.Queue] = {}
project_latest_event: Dict[str, dict] = {}

def get_project_queue(project_id: str) -> asyncio.Queue:
    if project_id not in project_queues:
        project_queues[project_id] = asyncio.Queue()
    return project_queues[project_id]

async def publish_event(project_id: str, stage: str, progress: float, message: str, current_chunk: int = 0, total_chunks: int = 0, triples_found: int = 0):
    event_data = {
        "project_id": project_id,
        "stage": stage,
        "progress": round(progress, 3),
        "message": message,
        "current_chunk": current_chunk,
        "total_chunks": total_chunks,
        "triples_found": triples_found,
        "timestamp": time.time()
    }
    project_latest_event[project_id] = event_data
    queue = get_project_queue(project_id)
    await queue.put(event_data)

def run_extraction_pipeline_sync(
    project_id: str,
    provider: str,
    endpoint: str,
    api_key: str,
    model_name: str,
    loop: asyncio.AbstractEventLoop,
    ner_mode: str = "advanced"
):
    db: Session = SessionLocal()
    start_time = time.time()
    ner_mode = (ner_mode or "advanced").lower()
    mode_label = "Basic (4 core types)" if ner_mode == "basic" else "Advanced (35 ontologies)"

    def emit(stage: str, progress: float, message: str, current_chunk: int = 0, total_chunks: int = 0, triples_found: int = 0):
        try:
            asyncio.run_coroutine_threadsafe(
                publish_event(project_id, stage, progress, message, current_chunk, total_chunks, triples_found),
                loop
            )
        except Exception as err:
            logger.warning(f"Failed to publish event to SSE: {err}")

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return

        project.status = "processing"
        project.provider = provider
        project.model = model_name
        project.ner_mode = ner_mode
        db.commit()

        # Step 1: Docling PDF Extraction
        emit("docling", 0.05, "Parsing PDF documents with IBM Docling...", 0, 0, 0)
        
        all_chunks_data = []  # [(doc_obj, chunk_index, chunk_text)]
        full_text_corpus = []

        for doc in project.documents:
            try:
                with open(doc.file_path, "rb") as f:
                    file_bytes = f.read()
                chunks = extract_text_from_pdf(file_bytes, filename=doc.filename)
                doc.chunks_count = len(chunks)
                db.commit()

                # Clear any existing chunks for this document before inserting
                db.query(Chunk).filter(Chunk.document_id == doc.id).delete()
                for idx, c in enumerate(chunks):
                    chunk_obj = Chunk(
                        document_id=doc.id,
                        chunk_index=idx,
                        raw_text=c
                    )
                    db.add(chunk_obj)
                    all_chunks_data.append((doc, idx, c))
                    full_text_corpus.append(c)
                db.commit()
            except Exception as e:
                logger.error(f"Docling extraction failed for {doc.filename}: {e}")

        total_chunks = len(all_chunks_data)
        if total_chunks == 0:
            emit("error", 1.0, "No valid text could be extracted from uploaded PDF(s).", 0, 0, 0)
            project.status = "failed"
            db.commit()
            return

        project.total_chunks = total_chunks
        db.commit()

        emit("ner_gliner", 0.15, f"Split into {total_chunks} structured chunks. Extracting [{mode_label}] entities & triples with GLiNER & {model_name}...", 0, total_chunks, 0)

        # Step 2: Extraction Loop (LLM Cleaning + Parallel GLiNER NER & LLM Triples)
        raw_triples = []
        global_entities = {}
        last_llm_error: Optional[str] = None
        consecutive_llm_errors = 0

        for idx, (doc, c_idx, raw_chunk) in enumerate(all_chunks_data):
            progress_ratio = 0.15 + ((idx) / total_chunks) * 0.50
            emit("llm_triples", progress_ratio, f"Processing Chunk {idx+1}/{total_chunks}: extracting [{mode_label}] entities & triples with GLiNER and {model_name}...", idx + 1, total_chunks, len(raw_triples))

            # 2a. Deterministic Non-LLM Text Normalization & De-fragmentation
            cleaned_text = clean_and_defragment_text(raw_chunk)
            if not cleaned_text.strip():
                cleaned_text = raw_chunk.strip()

            if not cleaned_text:
                continue

            # 2b. GLiNER high-precision entity extraction followed by GLiNER-grounded LLM Triple extraction
            chunk_entities_detailed = extract_entities_detailed(cleaned_text, ner_mode=ner_mode)
            for item in chunk_entities_detailed:
                global_entities[item["text"].lower()] = item["type"]

            # Provide clean entity names without category annotations
            candidate_names = [
                sanitize_entity_name(item["text"])
                for item in chunk_entities_detailed
                if sanitize_entity_name(item["text"]).lower() not in BLACKLISTED_ENTITIES
            ]

            try:
                chunk_triples = extract_triples_and_evidence_llm(
                    cleaned_text, endpoint, api_key, model_name, candidate_entities=candidate_names, provider=provider, ner_mode=ner_mode
                )
                consecutive_llm_errors = 0
            except Exception as e:
                last_llm_error = str(e)
                consecutive_llm_errors += 1
                logger.error(f"LLM triples error on chunk {idx+1}/{total_chunks}: {e}")

                err_lower = last_llm_error.lower()
                is_auth_error = any(k in err_lower for k in ["unauthorized", "authentication", "api_key", "401", "invalid_api_key", "forbidden", "403", "payment", "402"])
                is_conn_error = any(k in err_lower for k in ["connection refused", "failed to connect", "errno 61", "errno 111", "not found", "404"])

                if (is_auth_error or is_conn_error) and (idx == 0 or consecutive_llm_errors >= 2):
                    raise RuntimeError(f"LLM request failed: {last_llm_error}")

                chunk_triples = []

            for t in chunk_triples:
                raw_e1 = sanitize_entity_name(
                    t.get("entity1") or t.get("subject") or t.get("head") or t.get("source") or t.get("entity_1") or ""
                )
                raw_rel = (
                    t.get("relationship") or t.get("predicate") or t.get("relation") or t.get("rel") or t.get("type") or ""
                ).strip()
                raw_e2 = sanitize_entity_name(
                    t.get("entity2") or t.get("object") or t.get("tail") or t.get("target") or t.get("entity_2") or ""
                )
                evidence = (
                    t.get("evidence") or t.get("sentence") or t.get("context") or t.get("source_sentence") or cleaned_text[:250]
                ).strip()

                if not raw_e1 or not raw_e2 or raw_e1.lower() == raw_e2.lower():
                    continue
                if raw_e1.lower() in BLACKLISTED_ENTITIES or raw_e2.lower() in BLACKLISTED_ENTITIES:
                    continue

                rel = normalize_rel(raw_rel)

                # Snap LLM entities to GLiNER exact spans with safe modifier handling
                snapped_e1, type1 = snap_entity_to_gliner_spans(raw_e1, chunk_entities_detailed)
                snapped_e2, type2 = snap_entity_to_gliner_spans(raw_e2, chunk_entities_detailed)

                snapped_e1 = sanitize_entity_name(snapped_e1)
                snapped_e2 = sanitize_entity_name(snapped_e2)

                if snapped_e1 and snapped_e2 and snapped_e1.lower() != snapped_e2.lower():
                    if snapped_e1.lower() not in BLACKLISTED_ENTITIES and snapped_e2.lower() not in BLACKLISTED_ENTITIES:
                        if ner_mode == "basic":
                            b_type1 = normalize_to_basic_type(snapped_e1, type1)
                            b_type2 = normalize_to_basic_type(snapped_e2, type2)
                            if not b_type1 or not b_type2:
                                continue
                            type1 = b_type1
                            type2 = b_type2
                        raw_triples.append({
                            "document_id": doc.id,
                            "entity1": snapped_e1,
                            "entity1_type": type1,
                            "relationship": rel,
                            "entity2": snapped_e2,
                            "entity2_type": type2,
                            "color": get_relationship_color(rel),
                            "evidence": evidence
                        })

        if len(raw_triples) == 0 and last_llm_error:
            raise RuntimeError(f"Extraction yielded 0 triples because LLM calls failed: {last_llm_error}")

        # Step 3: Non-LLM Normalization Engine
        emit("normalizer", 0.70, f"Normalizing {len(raw_triples)} triples with ScispaCy & HGNC/MeSH dictionaries...", total_chunks, total_chunks, len(raw_triples))
        unique_entities = set()
        for r in raw_triples:
            unique_entities.add(r["entity1"])
            unique_entities.add(r["entity2"])

        full_doc_context = "\n".join(full_text_corpus)
        alias_mapping = normalize_entities_non_llm(unique_entities, full_doc_context)

        # Apply canonical mapping and deduplicate
        SYMMETRIC_RELATIONS = {"associated_with", "interacts_with", "coexists_with"}
        seen_triples = set()
        deduped_triples = []
        for r in raw_triples:
            e1 = alias_mapping.get(r["entity1"], r["entity1"]).strip()
            e2 = alias_mapping.get(r["entity2"], r["entity2"]).strip()
            r["entity1"] = e1
            r["entity2"] = e2
            rel_name = r["relationship"].lower().strip()

            if not e1 or not e2 or e1.lower() == e2.lower():
                continue

            if rel_name in SYMMETRIC_RELATIONS:
                # Canonicalize pair order so (A, rel, B) and (B, rel, A) share the same unique key
                pair_key = tuple(sorted([e1.lower(), e2.lower()]))
                key = (pair_key, rel_name)
            else:
                key = (e1.lower(), rel_name, e2.lower())

            if key not in seen_triples:
                seen_triples.add(key)
                deduped_triples.append(r)

        # Step 4: PubMed Citation Enrichment
        emit("pubmed", 0.80, f"Querying NCBI PubMed for {len(deduped_triples)} relationships...", total_chunks, total_chunks, len(deduped_triples))
        pmid_cache = {}
        for idx, t in enumerate(deduped_triples):
            pmid_progress = 0.80 + (idx / max(len(deduped_triples), 1)) * 0.12
            emit("pubmed", pmid_progress, f"Querying PubMed: {t['entity1']} + {t['entity2']}...", total_chunks, total_chunks, len(deduped_triples))
            pair_key = tuple(sorted([t["entity1"].lower(), t["entity2"].lower()]))
            if pair_key in pmid_cache:
                pmids = pmid_cache[pair_key]
            else:
                pmids = fetch_pubmed_ids_for_triple(t["entity1"], t["entity2"])
                pmid_cache[pair_key] = pmids
            t["pubmed_ids"] = pmids

        # Step 5: Database Persistence (SQLite/PostgreSQL + Neo4j)
        emit("neo4j", 0.94, "Writing knowledge graph to Neo4j and relational database...", total_chunks, total_chunks, len(deduped_triples))
        
        # Write to SQLite/Postgres
        db.query(Triple).filter(Triple.project_id == project_id).delete()
        for t in deduped_triples:
            triple_obj = Triple(
                project_id=project_id,
                document_id=t.get("document_id"),
                entity1=t["entity1"],
                entity1_type=t["entity1_type"],
                relationship_name=t["relationship"],
                entity2=t["entity2"],
                entity2_type=t["entity2_type"],
                evidence=t.get("evidence", ""),
                pubmed_ids=t.get("pubmed_ids", "")
            )
            db.add(triple_obj)

        # Write to Neo4j
        sync_triples_to_neo4j(project_id, deduped_triples, ner_mode=ner_mode)

        # Finalize project metadata
        exec_time = time.time() - start_time
        project.status = "completed"
        project.total_triples = len(deduped_triples)
        project.execution_time = exec_time
        db.commit()

        emit("completed", 1.0, f"Extraction complete! {len(deduped_triples)} triples extracted.", total_chunks, total_chunks, len(deduped_triples))

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        try:
            db.rollback()
            p = db.query(Project).filter(Project.id == project_id).first()
            if p:
                p.status = "failed"
                db.commit()
        except Exception as db_err:
            logger.error(f"Failed to record project failure: {db_err}")
        emit("error", 1.0, f"Extraction failed: {str(e)}", 0, 0, 0)
    finally:
        db.close()


@router.post("/{project_id}/extract")
async def start_extraction(project_id: str, payload: ExtractionRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.documents:
        raise HTTPException(status_code=400, detail="Please upload at least one PDF before starting extraction.")

    # Auto-resolve missing credentials and endpoints from GlobalSetting
    db_settings = {s.key: s.value for s in db.query(GlobalSetting).all()}

    provider = (payload.provider or "").strip()
    if not provider:
        provider = db_settings.get("default_provider", "LM Studio")

    endpoint = (payload.endpoint or "").strip()
    api_key = (payload.api_key or "").strip()
    model_name = (payload.model or "").strip()

    prov_lower = provider.lower()
    if "openrouter" in prov_lower:
        if not endpoint:
            endpoint = db_settings.get("openrouter_endpoint") or "https://openrouter.ai/api/v1"
        if not api_key:
            api_key = db_settings.get("openrouter_api_key") or os.getenv("OPENROUTER_API_KEY", "")
    elif "ollama" in prov_lower:
        saved_key = db_settings.get("ollama_api_key") or os.getenv("OLLAMA_API_KEY", "")
        if not api_key and saved_key:
            api_key = saved_key
        if not endpoint:
            if api_key or "ollama.com" in (db_settings.get("ollama_endpoint") or ""):
                endpoint = db_settings.get("ollama_endpoint") or "https://ollama.com/v1"
            else:
                endpoint = db_settings.get("ollama_endpoint") or "http://localhost:11434"
        if "ollama.com" in endpoint.lower() and not endpoint.rstrip("/").endswith("/v1"):
            endpoint = f"{endpoint.rstrip('/')}/v1"
    elif "lm studio" in prov_lower:
        if not endpoint:
            endpoint = db_settings.get("lmstudio_endpoint") or "http://localhost:1234/v1"
        if not api_key:
            api_key = "not-needed"
    elif "openai" in prov_lower:
        if not endpoint:
            endpoint = db_settings.get("openai_endpoint") or "https://api.openai.com/v1"
        if not api_key:
            api_key = db_settings.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")
    elif "anthropic" in prov_lower:
        if not api_key:
            api_key = db_settings.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY", "")
    elif "gemini" in prov_lower or "google" in prov_lower:
        if not api_key:
            api_key = db_settings.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", "")
    elif "groq" in prov_lower:
        if not api_key:
            api_key = db_settings.get("groq_api_key") or os.getenv("GROQ_API_KEY", "")
    elif "mistral" in prov_lower:
        if not api_key:
            api_key = db_settings.get("mistral_api_key") or os.getenv("MISTRAL_API_KEY", "")

    endpoint = adapt_endpoint_for_docker(endpoint)

    if not model_name:
        model_name = "gpt-4o-mini"

    ner_mode = (payload.ner_mode or project.ner_mode or "advanced").lower().strip()
    if ner_mode not in ("basic", "advanced"):
        ner_mode = "advanced"
    project.ner_mode = ner_mode
    db.commit()

    loop = asyncio.get_running_loop()

    # Clear old queue state for fresh run
    project_queues[project_id] = asyncio.Queue()
    project_latest_event[project_id] = {
        "project_id": project_id,
        "stage": "docling",
        "progress": 0.05,
        "message": "Initializing extraction pipeline...",
        "current_chunk": 0,
        "total_chunks": 0,
        "triples_found": 0,
        "timestamp": time.time()
    }

    background_tasks.add_task(
        run_extraction_pipeline_sync,
        project_id,
        provider,
        endpoint,
        api_key,
        model_name,
        loop,
        ner_mode
    )

    return {"status": "started", "project_id": project_id, "ner_mode": ner_mode}


@router.get("/{project_id}/status")
def get_project_status(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    latest_event = project_latest_event.get(project_id)
    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "total_chunks": project.total_chunks,
        "total_triples": project.total_triples,
        "execution_time": project.execution_time,
        "latest_event": latest_event
    }


@router.get("/{project_id}/progress")
async def stream_progress(project_id: str, db: Session = Depends(get_db)):
    queue = get_project_queue(project_id)
    initial_event = project_latest_event.get(project_id)

    async def event_generator():
        # Yield initial state immediately if available
        if initial_event:
            yield f"data: {json.dumps(initial_event)}\n\n"
            if initial_event.get("stage") in ("completed", "error"):
                return

        while True:
            try:
                event_data = await asyncio.wait_for(queue.get(), timeout=15.0)
                yield f"data: {json.dumps(event_data)}\n\n"
                if event_data.get("stage") in ("completed", "error"):
                    break
            except asyncio.TimeoutError:
                # Keep-alive heartbeat to prevent proxy timeout
                yield f": heartbeat\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
