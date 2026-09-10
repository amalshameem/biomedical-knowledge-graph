import os
import json
import re
import time
import logging
import requests
from typing import List, Dict, Any
import litellm
from openai import OpenAI
from app.services.ner_service import BLACKLISTED_ENTITIES

logger = logging.getLogger(__name__)

# Configure LiteLLM
litellm.telemetry = False
litellm.suppress_debug_info = True
litellm.drop_params = True

import ast

VALID_RELATIONSHIPS = {
    "treats", "causes", "predisposes", "interacts_with",
    "associated_with", "positively_regulates", "negatively_regulates",
    "expressed_in", "coexists_with"
}

def normalize_rel(r: str) -> str:
    """
    Standardizes any natural-language biomedical relationship into one of the 9 ontology categories:
    ['treats', 'causes', 'predisposes', 'interacts_with', 'associated_with',
     'positively_regulates', 'negatively_regulates', 'expressed_in', 'coexists_with']
    """
    if not r:
        return "associated_with"
    clean_r = str(r).lower().strip().replace(" ", "_").replace("-", "_")
    if clean_r in VALID_RELATIONSHIPS:
        return clean_r

    # 1. Negative regulation / inhibition / downregulation
    if any(k in clean_r for k in [
        "negatively_regulate", "negative_regulation", "inhibit", "suppress",
        "downregulat", "down_regulat", "block", "reduc", "decreas", "silenc",
        "attenuat", "repress", "antagoniz"
    ]):
        return "negatively_regulates"

    # 2. Positive regulation / activation / upregulation
    if any(k in clean_r for k in [
        "positively_regulate", "positive_regulation", "upregulat", "up_regulat",
        "activat", "stimulat", "promot", "enhanc", "increas", "augmen",
        "induc", "elevat", "trigger"
    ]):
        return "positively_regulates"

    # 3. Treatment / therapy
    if any(k in clean_r for k in [
        "treat", "cur", "therap", "ameliorat", "rescu", "revers", "alleviat", "remed"
    ]):
        return "treats"

    # 4. Causation / pathogenesis
    if any(k in clean_r for k in [
        "caus", "lead_to", "leads_to", "pathogen", "etiolog"
    ]):
        return "causes"

    # 5. Predisposition / risk factor
    if any(k in clean_r for k in [
        "predispos", "risk", "susceptib", "vulnerab"
    ]):
        return "predisposes"

    # 6. Physical or molecular interaction / binding
    if any(k in clean_r for k in [
        "bind", "interact", "complex", "target", "attach", "ligand", "cleav"
    ]):
        return "interacts_with"

    # 7. Expression / localization
    if any(k in clean_r for k in [
        "express", "locali", "found_in", "present_in", "secret", "produc_in"
    ]):
        return "expressed_in"

    # 8. Comorbidity / co-existence
    if any(k in clean_r for k in [
        "coexist", "comorbid", "cooccur", "co_occur", "concomitant"
    ]):
        return "coexists_with"

    return "associated_with"

def is_in_docker() -> bool:
    """Detect if the application is running inside a Docker container."""
    return (
        os.path.exists('/.dockerenv')
        or os.environ.get('IN_DOCKER', '').lower() in ('true', '1')
        or 'postgres:5432' in os.environ.get('DATABASE_URL', '')
    )

def adapt_endpoint_for_docker(url: str) -> str:
    """
    If running inside a Docker container, automatically translate 'localhost' or '127.0.0.1'
    to 'host.docker.internal' so the container can connect to local LLM providers
    (LM Studio on port 1234, Ollama on port 11434, etc.) running on the host machine.
    """
    if not url or not is_in_docker():
        return url
    return re.sub(r'://(localhost|127\.0\.0\.1)(:\d+)?', r'://host.docker.internal\2', url)

def resolve_litellm_model_and_params(
    model_name: str,
    endpoint: str = "",
    api_key: str = "",
    provider: str = ""
) -> Dict[str, Any]:
    """
    Standardizes model names, prefixes, and endpoints for LiteLLM completion calls.
    Supports OpenRouter, Ollama (Local & Cloud), LM Studio, Anthropic, Gemini, Groq, Mistral, OpenAI, etc.
    Guarantees required credentials so LiteLLM and underlying providers execute without errors.
    """
    endpoint = adapt_endpoint_for_docker(endpoint)
    params: Dict[str, Any] = {}
    m = (model_name or "").strip()
    if not m:
        m = "gpt-4o-mini"

    endpoint_lower = (endpoint or "").lower()
    api_key_clean = (api_key or "").strip()
    prov_lower = (provider or "").lower()

    # 1. OpenRouter
    if "openrouter" in prov_lower or "openrouter" in endpoint_lower or (api_key_clean and api_key_clean.startswith("sk-or-")):
        clean_model = m.replace("openrouter/", "")
        params["model"] = f"openrouter/{clean_model}"
        params["api_base"] = endpoint if endpoint else "https://openrouter.ai/api/v1"
        params["api_key"] = api_key_clean

    # 2. Ollama Cloud (API key provided, or endpoint points to ollama.com)
    elif "ollama.com" in endpoint_lower or ("ollama" in prov_lower and api_key_clean and api_key_clean != "not-needed"):
        clean_model = m.replace("ollama_chat/", "").replace("ollama/", "").replace("openai/", "")
        params["model"] = f"openai/{clean_model}"
        base = endpoint.strip().rstrip("/") if endpoint else "https://ollama.com/v1"
        if "ollama.com" in base and not base.endswith("/v1"):
            base = f"{base}/v1"
        params["api_base"] = base
        params["api_key"] = api_key_clean

    # 3. Local Ollama (no key, or localhost / port 11434)
    elif "ollama" in prov_lower or "11434" in endpoint_lower or "ollama" in endpoint_lower:
        clean_model = m.replace("ollama_chat/", "").replace("ollama/", "")
        params["model"] = f"ollama_chat/{clean_model}"
        default_ollama = adapt_endpoint_for_docker("http://localhost:11434")
        params["api_base"] = endpoint if endpoint else default_ollama
        params["api_key"] = api_key_clean if api_key_clean else "not-needed"

    # 4. Groq
    elif "groq" in prov_lower or "groq.com" in endpoint_lower or (api_key_clean and api_key_clean.startswith("gsk_")):
        clean_model = m.replace("groq/", "")
        params["model"] = f"groq/{clean_model}"
        params["api_key"] = api_key_clean
        if endpoint and "groq.com" not in endpoint:
            params["api_base"] = endpoint

    # 5. Mistral AI
    elif "mistral" in prov_lower or "mistral.ai" in endpoint_lower:
        clean_model = m.replace("mistral/", "")
        params["model"] = f"mistral/{clean_model}"
        params["api_key"] = api_key_clean
        if endpoint and "mistral.ai" not in endpoint:
            params["api_base"] = endpoint

    # 6. Anthropic
    elif "anthropic" in prov_lower or "anthropic.com" in endpoint_lower or (api_key_clean and api_key_clean.startswith("sk-ant-")):
        clean_model = m.replace("anthropic/", "")
        params["model"] = f"anthropic/{clean_model}"
        params["api_key"] = api_key_clean

    # 7. Google Gemini
    elif "gemini" in prov_lower or "google" in prov_lower or "generativelanguage.googleapis.com" in endpoint_lower or (api_key_clean and api_key_clean.startswith("AIzaSy")):
        clean_model = m.replace("gemini/", "").replace("models/", "")
        params["model"] = f"gemini/{clean_model}"
        params["api_key"] = api_key_clean

    # 8. LM Studio (Local)
    elif "lm studio" in prov_lower or "1234" in endpoint_lower:
        clean_model = m.replace("openai/", "")
        params["model"] = f"openai/{clean_model}"
        default_lm = adapt_endpoint_for_docker("http://localhost:1234/v1")
        params["api_base"] = endpoint if endpoint else default_lm
        params["api_key"] = api_key_clean if api_key_clean else "not-needed"


    # 9. Generic Custom OpenAI endpoint
    elif endpoint:
        clean_model = m.replace("openai/", "")
        params["model"] = f"openai/{clean_model}"
        params["api_base"] = endpoint
        params["api_key"] = api_key_clean if api_key_clean else "not-needed"

    # 10. Default OpenAI
    else:
        clean_model = m.replace("openai/", "")
        params["model"] = f"openai/{clean_model}"
        params["api_key"] = api_key_clean if api_key_clean else "not-needed"

    return params

def parse_llm_json(response_content: str) -> List[Dict[str, Any]]:
    """
    Robust JSON parser for LLM outputs. Handles markdown code fences, embedded JSON arrays,
    wrapper objects like {"triples": [...]}, single dictionary triples, trailing commas, and single quotes.
    """
    if not response_content:
        return []
    text = response_content.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\s*```$', '', text).strip()

    def unpack_data(data) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for k in ("triples", "relationships", "extracted_triples", "data", "results", "output"):
                if k in data and isinstance(data[k], list):
                    return [x for x in data[k] if isinstance(x, dict)]
            if any(k in data for k in ("entity1", "subject", "head", "source", "entity_1")):
                return [data]
        return []

    # 1. Direct json.loads
    try:
        data = json.loads(text)
        res = unpack_data(data)
        if res:
            return res
    except Exception:
        pass

    # 2. Fix trailing commas and retry
    try:
        fixed = re.sub(r',\s*([\]}])', r'\1', text)
        data = json.loads(fixed)
        res = unpack_data(data)
        if res:
            return res
    except Exception:
        pass

    # 3. Search for bracket range [ ... ]
    s_b, e_b = text.find('['), text.rfind(']')
    if s_b != -1 and e_b > s_b:
        bracket_sub = text[s_b:e_b + 1]
        try:
            data = json.loads(bracket_sub)
            res = unpack_data(data)
            if res:
                return res
        except Exception:
            try:
                fixed = re.sub(r',\s*([\]}])', r'\1', bracket_sub)
                data = json.loads(fixed)
                res = unpack_data(data)
                if res:
                    return res
            except Exception:
                pass

    # 4. Search for brace range { ... }
    s_c, e_c = text.find('{'), text.rfind('}')
    if s_c != -1 and e_c > s_c:
        brace_sub = text[s_c:e_c + 1]
        try:
            data = json.loads(brace_sub)
            res = unpack_data(data)
            if res:
                return res
        except Exception:
            try:
                fixed = re.sub(r',\s*([\]}])', r'\1', brace_sub)
                data = json.loads(fixed)
                res = unpack_data(data)
                if res:
                    return res
            except Exception:
                pass

    # 5. ast.literal_eval fallback for Python dictionary/list syntax
    try:
        data = ast.literal_eval(text)
        res = unpack_data(data)
        if res:
            return res
    except Exception:
        pass

    return []

def _is_chat_model(model_id: str) -> bool:
    """Filter out non-chat models (image generators, embeddings, TTS, moderation, etc.)."""
    m = model_id.lower()
    skip_patterns = [
        "dall-e", "tts-", "whisper", "embedding", "moderation", "davinci-002",
        "babbage-002", "gpt-image", "imagen", "sora", "ft:", "codex-mini",
        "realtime", "transcribe", "translate", "audio", "/dall-e", "nano-banana",
        ":batch", "daybreak", "gpt-live", "omni-moderation",
        # Size/resolution prefixes from OpenAI
        "256-x-", "512-x-", "1024-x-", "1536-x-", "1792-x-",
        "low/", "medium/", "high/", "standard/", "hd/",
    ]
    return not any(pat in m for pat in skip_patterns)


def fetch_models(provider: str, endpoint: str = "", api_key: str = "") -> List[str]:
    """
    Dynamically fetches models exclusively from live provider APIs when credentials/endpoints are given:
    - No static/pre-defined model fallback sets.
    - Cloud providers (OpenAI, Anthropic, Gemini, Groq, Mistral, Ollama Cloud): Requires API key to fetch live models.
    - Local providers (LM Studio, local Ollama): Queries local server if running.
    - Ollama Cloud: When API key is provided, queries https://ollama.com/api/tags with Bearer auth.
    """
    models: List[str] = []
    p = (provider or "").strip()
    api_key = (api_key or "").strip()
    endpoint = adapt_endpoint_for_docker((endpoint or "").strip())

    # Cloud providers require an API key to dynamically fetch models
    cloud_providers = ["OpenAI", "Anthropic", "Google Gemini", "Groq", "Mistral AI"]
    if p in cloud_providers and not api_key:
        logger.info(f"{p}: No API key provided, skipping live model fetch.")
        return []

    try:
        # ── Ollama (Local & Cloud) ──────────────────────────────────
        if p == "Ollama":
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            
            # If an API key is provided, prioritize Ollama Cloud endpoints
            if api_key:
                cloud_urls = [
                    "https://ollama.com/api/tags",
                    "https://ollama.com/v1/models",
                    "https://api.ollama.com/api/tags",
                ]
                # Also check custom endpoint if specified and not localhost
                if endpoint and "localhost" not in endpoint and "127.0.0.1" not in endpoint and "host.docker.internal" not in endpoint:
                    clean_ep = re.sub(r'/(v1|api)/?$', '', endpoint.rstrip('/'))
                    cloud_urls.insert(0, f"{clean_ep}/api/tags")
                    cloud_urls.insert(1, f"{clean_ep}/v1/models")

                for url in cloud_urls:
                    try:
                        r = requests.get(url, headers=headers, timeout=8)
                        if r.status_code == 200:
                            data = r.json()
                            if "models" in data and isinstance(data["models"], list):
                                models = [m.get("name") or m.get("model") for m in data["models"] if isinstance(m, dict)]
                            elif "data" in data and isinstance(data["data"], list):
                                models = [m.get("id") for m in data["data"] if isinstance(m, dict) and m.get("id")]
                            if models:
                                logger.info(f"Ollama Cloud: fetched {len(models)} live models from {url}")
                                break
                    except Exception as e:
                        logger.debug(f"Ollama Cloud attempt at {url} failed: {e}")

            # If no API key, or if cloud attempt didn't yield models, check local Ollama server
            if not models and not api_key:
                default_ollama = adapt_endpoint_for_docker("http://localhost:11434")
                local_ep = re.sub(r'/(v1|api)/?$', '', (endpoint or default_ollama).rstrip('/'))
                for sub in ["/api/tags", "/v1/models"]:
                    try:
                        r = requests.get(f"{local_ep}{sub}", headers=headers, timeout=3)
                        if r.status_code == 200:
                            data = r.json()
                            if "models" in data:
                                models = [m.get("name") or m.get("model") for m in data["models"] if isinstance(m, dict)]
                            elif "data" in data:
                                models = [m.get("id") for m in data["data"] if isinstance(m, dict) and m.get("id")]
                            if models:
                                logger.info(f"Local Ollama: fetched {len(models)} live models from {local_ep}{sub}")
                                break
                    except Exception:
                        continue

        # ── LM Studio (Local) ──────────────────────────────────────
        elif p == "LM Studio":
            default_lm = adapt_endpoint_for_docker("http://localhost:1234")
            clean_ep = re.sub(r'/(v1|api/v0|models)/?$', '', (endpoint or default_lm).rstrip('/'))

            for sub in ["/v1/models", "/api/v0/models", "/models"]:
                try:
                    r = requests.get(f"{clean_ep}{sub}", timeout=3)
                    if r.status_code == 200:
                        data = r.json()
                        raw_data = data.get("data") or data.get("models") or []
                        if isinstance(raw_data, list):
                            models = [m.get("id") or m.get("name") for m in raw_data if isinstance(m, dict) and (m.get("id") or m.get("name"))]
                        if models:
                            logger.info(f"LM Studio: fetched {len(models)} live models from {clean_ep}{sub}")
                            break
                except Exception:
                    continue

        # ── OpenRouter ──────────────────────────────────────────────
        elif p == "OpenRouter":
            ep = endpoint or "https://openrouter.ai/api/v1"
            url = f"{ep.rstrip('/')}/models" if not ep.endswith("/models") else ep
            h = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            try:
                r = requests.get(url, headers=h, timeout=8)
                if r.status_code == 200:
                    raw = [m["id"] for m in r.json().get("data", []) if isinstance(m, dict) and "id" in m]
                    models = [m for m in raw if ":free" not in m and ":beta" not in m]
                    logger.info(f"OpenRouter: fetched {len(models)} live models")
            except Exception as e:
                logger.warning(f"OpenRouter fetch error: {e}")

        # ── Anthropic ───────────────────────────────────────────────
        elif p == "Anthropic":
            if api_key:
                ep = endpoint or "https://api.anthropic.com/v1"
                url = f"{ep.rstrip('/')}/models" if not ep.endswith("/models") else ep
                try:
                    r = requests.get(url, headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"}, timeout=8)
                    if r.status_code == 200:
                        models = [m.get("id") for m in r.json().get("data", []) if isinstance(m, dict) and m.get("id")]
                        logger.info(f"Anthropic: fetched {len(models)} live models")
                    else:
                        logger.warning(f"Anthropic API returned {r.status_code}: {r.text[:200]}")
                except Exception as e:
                    logger.warning(f"Anthropic fetch error: {e}")

        # ── Google Gemini ───────────────────────────────────────────
        elif p == "Google Gemini":
            if api_key:
                ep = endpoint or "https://generativelanguage.googleapis.com"
                url = f"{ep.rstrip('/')}/v1beta/models?key={api_key}"
                try:
                    r = requests.get(url, timeout=8)
                    if r.status_code == 200:
                        raw = r.json().get("models", [])
                        models = [
                            m.get("name", "").replace("models/", "")
                            for m in raw
                            if isinstance(m, dict) and "generateContent" in m.get("supportedGenerationMethods", [])
                        ]
                        logger.info(f"Google Gemini: fetched {len(models)} live models")
                    else:
                        logger.warning(f"Google Gemini API returned {r.status_code}: {r.text[:200]}")
                except Exception as e:
                    logger.warning(f"Google Gemini fetch error: {e}")

        # ── OpenAI ──────────────────────────────────────────────────
        elif p == "OpenAI":
            if api_key:
                ep = endpoint or "https://api.openai.com/v1"
                url = f"{ep.rstrip('/')}/models" if not ep.endswith("/models") else ep
                try:
                    r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
                    if r.status_code == 200:
                        raw = [m.get("id") for m in r.json().get("data", []) if isinstance(m, dict) and m.get("id")]
                        models = [m for m in raw if _is_chat_model(m)]
                        logger.info(f"OpenAI: fetched {len(models)} live models")
                    else:
                        logger.warning(f"OpenAI API returned {r.status_code}: {r.text[:200]}")
                except Exception as e:
                    logger.warning(f"OpenAI fetch error: {e}")

        # ── Groq ────────────────────────────────────────────────────
        elif p == "Groq":
            if api_key:
                ep = endpoint or "https://api.groq.com/openai/v1"
                url = f"{ep.rstrip('/')}/models" if not ep.endswith("/models") else ep
                try:
                    r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
                    if r.status_code == 200:
                        models = [m.get("id") for m in r.json().get("data", []) if isinstance(m, dict) and m.get("id")]
                        logger.info(f"Groq: fetched {len(models)} live models")
                    else:
                        logger.warning(f"Groq API returned {r.status_code}: {r.text[:200]}")
                except Exception as e:
                    logger.warning(f"Groq fetch error: {e}")

        # ── Mistral AI ──────────────────────────────────────────────
        elif p == "Mistral AI":
            if api_key:
                ep = endpoint or "https://api.mistral.ai/v1"
                url = f"{ep.rstrip('/')}/models" if not ep.endswith("/models") else ep
                try:
                    r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=8)
                    if r.status_code == 200:
                        models = [m.get("id") for m in r.json().get("data", []) if isinstance(m, dict) and m.get("id")]
                        logger.info(f"Mistral AI: fetched {len(models)} live models")
                    else:
                        logger.warning(f"Mistral AI API returned {r.status_code}: {r.text[:200]}")
                except Exception as e:
                    logger.warning(f"Mistral AI fetch error: {e}")

    except Exception as e:
        logger.warning(f"Error fetching live models for {provider}: {e}")

    # Deduplicate while preserving order
    seen = set()
    unique_models = []
    for m in models:
        if m and m not in seen and not m.startswith("Error") and not m.startswith("Connection"):
            seen.add(m)
            unique_models.append(m)

    return unique_models

def extract_triples_and_evidence_llm(

    cleaned_text: str,
    endpoint: str,
    api_key: str,
    model_name: str,
    candidate_entities: List[str] = None,
    provider: str = "",
    ner_mode: str = "advanced"
) -> List[Dict[str, str]]:
    """
    Extracts biomedical relational triples with their verbatim source evidence sentence.
    Enforces standardized ontology terms for relationships and prioritizes verified candidate entities.
    Uses LiteLLM unified completion across OpenRouter, Ollama, LM Studio, Anthropic, Gemini, etc.
    """
    from app.services.ner_service import sanitize_entity_name

    if not cleaned_text.strip():
        return []

    system_prompt = (
        "You are an expert biomedical information extraction system. "
        "Extract relational triples along with the exact source sentence (evidence) from the text. "
        "Output ONLY a valid JSON array of objects with keys 'entity1', 'relationship', 'entity2', 'evidence'. "
        "Do NOT include any commentary, Markdown backticks, or extra text."
    )

    entities_hint = ""
    if candidate_entities and len(candidate_entities) > 0:
        # Strip any accidental type tags from candidate entities
        clean_candidates = [sanitize_entity_name(c) for c in candidate_entities if sanitize_entity_name(c)]
        clean_candidates = [c for c in clean_candidates if c.lower() not in BLACKLISTED_ENTITIES]
        if clean_candidates:
            entities_list_str = ", ".join(clean_candidates[:25])
            entities_hint = f"\nVERIFIED BIOMEDICAL ENTITIES IN THIS TEXT: [{entities_list_str}]\n"

    if (ner_mode or "").lower() == "basic":
        rule1 = (
            "1. Extract ONLY specific, named biomedical entities strictly belonging to: "
            "Diseases, Genes, Proteins, and Drugs (e.g. 'LCN2', 'IL-6', 'Infliximab', 'Crohn\'s Disease'). "
            "Do NOT extract pathways, tissues, cellular components, anatomical structures, or general biological concepts."
        )
    else:
        rule1 = (
            "1. Extract only specific, named biomedical entities (genes, proteins, chemicals, drugs, diseases, specific tissues, cell types). "
            "Use exact canonical names (e.g. 'LCN2', 'IL-6', 'TNF', 'NASH', 'colitis', 'adipocytes')."
        )

    user_prompt = f"""Extract relational triples and supporting evidence from the text below.{entities_hint}
Rules:
{rule1}
2. DO NOT extract generic procedural, experimental, or abstract words as entities (e.g. DO NOT extract 'neutralization', 'knockdown', 'synthesis', 'action', 'death', 'uptake', 'human', 'biomarker', 'murine model', 'type 1', 'protein', or 'resistance').
3. Multi-Target Decomposition: If a sentence lists multiple targets or cytokines (e.g. 'induces the synthesis of IL-1a, IL-6, IL-8, and TNF-a'), extract a separate individual triple for EACH individual target cytokine.
4. The 'relationship' MUST be one of the following standardized terminologies ONLY:
   - "treats"
   - "causes"
   - "predisposes"
   - "interacts_with"
   - "associated_with"
   - "positively_regulates"
   - "negatively_regulates"
   - "expressed_in"
   - "coexists_with"
   Do NOT invent other relationship types.
5. The 'evidence' field MUST be the exact verbatim sentence or clause from the text that proves this relationship.
6. If no valid triples exist, return [].

Format: JSON array of objects:
[{{"entity1": "...", "relationship": "...", "entity2": "...", "evidence": "..."}}]

Text:
"{cleaned_text}"

Output:"""

    call_params = resolve_litellm_model_and_params(model_name, endpoint, api_key, provider)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    last_err: Optional[Exception] = None

    for attempt in range(3):
        try:
            response = litellm.completion(
                messages=messages,
                temperature=0.1,
                timeout=120,
                num_retries=1,
                **call_params
            )
            content = response.choices[0].message.content
            raw_triples = parse_llm_json(content)

            valid = []
            for t in raw_triples:
                if not isinstance(t, dict):
                    continue
                e1 = sanitize_entity_name(
                    t.get("entity1") or t.get("subject") or t.get("head") or
                    t.get("source") or t.get("entity_1") or t.get("e1") or ""
                )
                raw_rel = (
                    t.get("relationship") or t.get("predicate") or t.get("relation") or
                    t.get("rel") or t.get("type") or t.get("interaction") or ""
                ).strip()
                e2 = sanitize_entity_name(
                    t.get("entity2") or t.get("object") or t.get("tail") or
                    t.get("target") or t.get("entity_2") or t.get("e2") or ""
                )
                evidence = (
                    t.get("evidence") or t.get("sentence") or t.get("context") or
                    t.get("source_sentence") or t.get("text") or ""
                ).strip()

                if e1 and raw_rel and e2 and e1.lower() != e2.lower():
                    if e1.lower() not in BLACKLISTED_ENTITIES and e2.lower() not in BLACKLISTED_ENTITIES:
                        rel = normalize_rel(raw_rel)
                        valid.append({
                            "entity1": e1,
                            "relationship": rel,
                            "entity2": e2,
                            "evidence": evidence or cleaned_text[:250]
                        })
            return valid
        except Exception as e:
            last_err = e
            logger.warning(f"LiteLLM triple extraction error attempt {attempt+1}: {e}")
            try:
                fallback_base = call_params.get("api_base") or endpoint or "http://localhost:1234/v1"
                fallback_key = call_params.get("api_key") or api_key or "not-needed"
                client = OpenAI(
                    base_url=fallback_base,
                    api_key=fallback_key,
                    timeout=120.0
                )
                clean_m = model_name.split("/")[-1] if "/" in model_name else model_name
                response = client.chat.completions.create(
                    model=clean_m,
                    messages=messages,
                    temperature=0.1
                )
                content = response.choices[0].message.content
                raw_triples = parse_llm_json(content)

                valid = []
                for t in raw_triples:
                    if not isinstance(t, dict):
                        continue
                    e1 = sanitize_entity_name(
                        t.get("entity1") or t.get("subject") or t.get("head") or
                        t.get("source") or t.get("entity_1") or t.get("e1") or ""
                    )
                    raw_rel = (
                        t.get("relationship") or t.get("predicate") or t.get("relation") or
                        t.get("rel") or t.get("type") or t.get("interaction") or ""
                    ).strip()
                    e2 = sanitize_entity_name(
                        t.get("entity2") or t.get("object") or t.get("tail") or
                        t.get("target") or t.get("entity_2") or t.get("e2") or ""
                    )
                    evidence = (
                        t.get("evidence") or t.get("sentence") or t.get("context") or
                        t.get("source_sentence") or t.get("text") or ""
                    ).strip()

                    if e1 and raw_rel and e2 and e1.lower() != e2.lower():
                        if e1.lower() not in BLACKLISTED_ENTITIES and e2.lower() not in BLACKLISTED_ENTITIES:
                            rel = normalize_rel(raw_rel)
                            valid.append({
                                "entity1": e1,
                                "relationship": rel,
                                "entity2": e2,
                                "evidence": evidence or cleaned_text[:250]
                            })
                if valid:
                    return valid
            except Exception as fb_err:
                last_err = fb_err
                logger.debug(f"Direct OpenAI fallback triple extraction failed: {fb_err}")
                if "ollama" in (provider or "").lower() or "ollama" in (endpoint or "").lower():
                    try:
                        clean_m = model_name.replace("ollama_chat/", "").replace("ollama/", "").replace("openai/", "")
                        ob = re.sub(r'/(v1|api)/?$', '', (endpoint or call_params.get("api_base") or "https://ollama.com").rstrip('/'))
                        oh = {"Content-Type": "application/json"}
                        if api_key:
                            oh["Authorization"] = f"Bearer {api_key}"
                        r = requests.post(
                            f"{ob}/api/chat",
                            headers=oh,
                            json={"model": clean_m, "messages": messages, "stream": False},
                            timeout=120
                        )
                        if r.status_code == 200:
                            content = r.json().get("message", {}).get("content", "")
                            raw_triples = parse_llm_json(content)
                            valid = []
                            for t in raw_triples:
                                if not isinstance(t, dict):
                                    continue
                                e1 = sanitize_entity_name(
                                    t.get("entity1") or t.get("subject") or t.get("head") or
                                    t.get("source") or t.get("entity_1") or t.get("e1") or ""
                                )
                                raw_rel = (
                                    t.get("relationship") or t.get("predicate") or t.get("relation") or
                                    t.get("rel") or t.get("type") or t.get("interaction") or ""
                                ).strip()
                                e2 = sanitize_entity_name(
                                    t.get("entity2") or t.get("object") or t.get("tail") or
                                    t.get("target") or t.get("entity_2") or t.get("e2") or ""
                                )
                                evidence = (
                                    t.get("evidence") or t.get("sentence") or t.get("context") or
                                    t.get("source_sentence") or t.get("text") or ""
                                ).strip()
                                if e1 and raw_rel and e2 and e1.lower() != e2.lower():
                                    if e1.lower() not in BLACKLISTED_ENTITIES and e2.lower() not in BLACKLISTED_ENTITIES:
                                        rel = normalize_rel(raw_rel)
                                        valid.append({
                                            "entity1": e1,
                                            "relationship": rel,
                                            "entity2": e2,
                                            "evidence": evidence or cleaned_text[:250]
                                        })
                            if valid:
                                return valid
                        else:
                            last_err = RuntimeError(f"Ollama returned HTTP {r.status_code}: {r.text[:200]}")
                    except Exception as o_err:
                        last_err = o_err
                        logger.debug(f"Direct Ollama /api/chat fallback failed: {o_err}")
            time.sleep(1.0 * (attempt + 1))

    if last_err is not None:
        raise last_err

    return []
