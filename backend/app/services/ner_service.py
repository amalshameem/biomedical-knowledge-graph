import re
import hashlib
import logging
from typing import Dict, Optional, List, Any, Tuple, Set

logger = logging.getLogger(__name__)

# Blacklisted non-specific or conversational tokens
BLACKLISTED_ENTITIES = {
    "patients", "patient", "study", "studies", "subjects", "participants",
    "trial", "trials", "cohort", "cohorts", "group", "groups",
    "control", "controls", "sample", "samples", "method", "methods",
    "analysis", "analyses", "experiment", "experiments", "protocol",
    "results", "result", "findings", "finding", "data", "outcome",
    "effect", "effects", "impact", "impacts", "response", "responses",
    "risk", "risks", "significant", "significance", "increased", "decreased",
    "role", "roles", "author", "authors", "paper", "papers", "article",
    "mice", "mouse", "rat", "rats", "we", "us", "our",
    "table", "figure", "fig", "supplementary",
    # Procedural & abstract linguistic noise
    "neutralization", "knockdown", "synthesis", "death", "action", "uptake",
    "expression", "level", "levels", "type 1", "protein", "proteins", "human", "humans",
    "murine model", "granule", "granules", "biomarker", "biomarkers", "fece", "feces",
    "model", "models", "therapy", "treatment", "inflammatory processe", "inflammatory pathway",
    "resistance", "damage", "lesion", "lesions", "secretion", "production", "presence",
    "mechanism", "mechanisms", "factor", "factors", "process", "processes",
    "disease", "diseases"
}

def sanitize_entity_name(name: str) -> str:
    """
    Cleans raw entity strings by removing category tag leaks (e.g. 'Inflammation (Disease)' -> 'Inflammation')
    and stripping trailing punctuation and quotes.
    """
    if not name:
        return ""
    s = name.strip().strip('"\'`')
    # Remove parenthetical category leaks (e.g. "Inflammation (Disease)" -> "Inflammation", "Intestinal (Organ)" -> "Intestinal")
    s = re.sub(r'\s*\((?:Gene|Protein|Enzyme|Receptor|Disease|Organ|Tissue|Cell|Chemical|Drug|Substance|Biological Process|Pathologic Function|Phenotypic Feature|Organism Taxon|Unknown|General Entity)\)\s*$', '', s, flags=re.IGNORECASE)
    # Collapse multiple spaces
    s = re.sub(r'\s+', ' ', s).strip()
    return s

# 35 specific biomedical labels
BIOMED_LABELS = [
    "Gene or Gene Product", "Protein", "Enzyme", "Receptor", "Nucleic Acid",
    "Chemical", "Drug", "Pharmacologic Substance", "Toxic Substance", "Biologic Function",
    "Cell", "Cellular Component", "Tissue", "Organ", "Anatomical Structure", "Body Fluid", "Substance",
    "Disease", "Syndrome", "Neoplasm", "Pathologic Function", "Sign or Symptom", "Clinical Finding",
    "Biological Process", "Molecular Function", "Pathway", "Metabolic Process",
    "Diagnostic Procedure", "Therapeutic Procedure", "Laboratory Procedure",
    "Organism Taxon", "Virus", "Bacterium",
    "Phenotypic Feature", "Environmental Effect"
]

_gliner_model = None

def get_ner_pipeline():
    global _gliner_model
    if _gliner_model is None:
        try:
            from gliner import GLiNER
            logger.info("Loading GLiNER BioMed Large model (Ihor/gliner-biomed-large-v1.0)...")
            _gliner_model = GLiNER.from_pretrained("Ihor/gliner-biomed-large-v1.0")
        except Exception as e:
            logger.error(f"Failed to load GLiNER: {e}")
            return None
    return _gliner_model

def normalize_string(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '', s.lower())

def get_best_ner_type(entity_text: str, chunk_entities: Dict[str, str]) -> str:
    """
    Finds the standard ontology type from chunk entities using exact, normalized,
    strict partial matches, or token intersection. Defaults to 'Unknown'.
    """
    if not entity_text or not chunk_entities:
        return "Unknown"

    e_lower = entity_text.lower().strip()
    if e_lower in chunk_entities:
        return chunk_entities[e_lower]

    e_norm = normalize_string(e_lower)

    # 1. Exact normalized match (handles IL-10 vs IL10)
    for ner_ent, ner_type in chunk_entities.items():
        if normalize_string(ner_ent) == e_norm:
            return ner_type

    # 2. Strict partial match by length ratio >= 0.5
    for ner_ent, ner_type in sorted(chunk_entities.items(), key=lambda x: len(x[0]), reverse=True):
        if (ner_ent in e_lower and len(ner_ent) / max(len(e_lower), 1) >= 0.5) or \
           (e_lower in ner_ent and len(e_lower) / max(len(ner_ent), 1) >= 0.5):
            return ner_type

    # 3. Word overlap for multi-word phrases (e.g. 'intestinal inflammation' -> 'inflammation')
    e_words = set(e_lower.split())
    for ner_ent, ner_type in sorted(chunk_entities.items(), key=lambda x: len(x[0]), reverse=True):
        ner_words = set(ner_ent.split())
        overlap = e_words.intersection(ner_words)
        meaningful_overlap = [w for w in overlap if len(w) > 3]
        if meaningful_overlap:
            return ner_type

    return "Unknown"

def extract_entities_detailed(text: str) -> List[Dict[str, Any]]:
    """
    Runs GLiNER NER on a text chunk and returns structured entity list with exact casing,
    type label, and confidence score.
    """
    if not text:
        return []

    entity_list = []
    seen = set()
    ner_model = get_ner_pipeline()
    if not ner_model:
        return []

    try:
        sentences = [s.strip() for s in re.split(r'\n|(?<=[.!?])\s+', text) if s.strip()]
        for sent in sentences:
            if len(sent) < 5:
                continue

            results = ner_model.predict_entities(sent, BIOMED_LABELS, threshold=0.3)
            for res in results:
                mapped = res.get("label", "").strip()
                score = float(res.get("score", 0))
                word = res.get("text", "").strip()

                if mapped and len(word) > 2 and word.lower() not in BLACKLISTED_ENTITIES:
                    k = (word.lower(), mapped)
                    if k not in seen:
                        seen.add(k)
                        entity_list.append({"text": word, "type": mapped, "score": score})
    except Exception as e:
        logger.error(f"NER extraction error: {e}")

    return entity_list

def extract_entities_from_text(text: str) -> Dict[str, str]:
    """
    Runs GLiNER NER on a text chunk using 35 specific biomedical labels.
    Returns mapping from entity text (lower) to entity type.
    """
    detailed = extract_entities_detailed(text)
    return {d["text"].lower(): d["type"] for d in detailed}

SAFE_SPECIFIERS = {
    "gene", "genes", "protein", "proteins", "mrna", "transcript", "transcripts",
    "levels", "level", "expression", "deficiency", "concentration", "concentrations",
    "production", "secretion", "sample", "samples", "tissue", "tissues",
    "serum", "fecal", "circulating", "activity", "activities"
}

PROTECTED_MODIFIERS = {
    "receptor", "receptors", "inhibitor", "inhibitors", "antagonist", "antagonists",
    "agonist", "agonists", "ligand", "ligands", "kinase", "kinases", "complex", "complexes",
    "antibody", "antibodies", "subunit", "subunits", "isoform", "isoforms",
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "0",
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta"
}

def snap_entity_to_gliner_spans(raw_entity: str, gliner_entities: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Snaps an LLM-extracted entity string to the high-precision GLiNER candidate span.
    Strips safe grammatical wrappers (gene, protein, expression, levels) while
    strictly preserving functional biological modifiers (receptor, inhibitor, COX-1 vs COX-2).
    Returns (snapped_entity_name, entity_type).
    """
    if not raw_entity or not raw_entity.strip():
        return ("", "Unknown")

    cleaned_raw = raw_entity.strip()
    raw_lower = cleaned_raw.lower()

    # 1. Exact match with a GLiNER candidate
    for g in gliner_entities:
        if g["text"].lower() == raw_lower:
            return (g["text"], g["type"])

    # 2. Check for GLiNER entity containment
    for g in sorted(gliner_entities, key=lambda x: len(x["text"]), reverse=True):
        g_text = g["text"]
        g_lower = g_text.lower()
        if g_lower in raw_lower:
            # Check the leftover words
            pattern = r'\b' + re.escape(g_lower) + r'\b'
            remaining = re.sub(pattern, '', raw_lower).strip()
            remaining_words = [w.strip("-_,;:()[]") for w in remaining.split() if w.strip("-_,;:()[]")]

            # If leftover words contain protected modifiers (e.g. "receptor", "inhibitor", "2"), DO NOT snap
            has_protected = any(w in PROTECTED_MODIFIERS for w in remaining_words)
            if has_protected:
                inferred_type = "Receptor" if "receptor" in remaining_words else ("Drug" if "inhibitor" in remaining_words else g["type"])
                return (cleaned_raw, inferred_type)

            # If all leftover words are safe non-distinguishing specifiers (or empty), snap to GLiNER exact text!
            all_safe = all(w in SAFE_SPECIFIERS for w in remaining_words)
            if all_safe or not remaining_words:
                return (g_text, g["type"])

    # 3. Fallback to best type match
    gliner_dict = {g["text"].lower(): g["type"] for g in gliner_entities}
    return (cleaned_raw, get_best_ner_type(cleaned_raw, gliner_dict))

RELATIONSHIP_COLORS = {
    "treats": "#0d9488",                # Teal (Therapeutic efficacy)
    "causes": "#be123c",                # Rose Red (Pathogenesis / Etiology)
    "predisposes": "#c2410c",           # Rust Orange (Risk factor / Susceptibility)
    "positively_regulates": "#15803d",  # Forest Green (Activation / Upregulation)
    "negatively_regulates": "#b91c1c",  # Crimson (Inhibition / Downregulation)
    "interacts_with": "#4f46e5",        # Deep Indigo (Direct molecular binding)
    "associated_with": "#6366f1",       # Soft Indigo (General correlation)
    "expressed_in": "#0284c7",          # Sky Cyan (Localization)
    "coexists_with": "#64748b",         # Slate Gray (Comorbidity)
}

def get_relationship_color(relationship: str) -> str:
    """
    Returns the distinct hex color code for any of the standard 9 biomedical relationships.
    """
    r = str(relationship).lower().strip().replace(" ", "_")
    return RELATIONSHIP_COLORS.get(r, "#6366f1")

TAXONOMY_MAP = {
    # 1. Genes & Molecular Entities
    "gene or gene product": {"category": "Genes & Molecular Entities", "sub_category": "Gene or Gene Product", "color": "#ef4444"},
    "gene": {"category": "Genes & Molecular Entities", "sub_category": "Gene or Gene Product", "color": "#ef4444"},
    "protein": {"category": "Genes & Molecular Entities", "sub_category": "Protein", "color": "#dc2626"},
    "enzyme": {"category": "Genes & Molecular Entities", "sub_category": "Enzyme", "color": "#b91c1c"},
    "receptor": {"category": "Genes & Molecular Entities", "sub_category": "Receptor", "color": "#f87171"},
    "nucleic acid": {"category": "Genes & Molecular Entities", "sub_category": "Nucleic Acid", "color": "#991b1b"},
    "transcription factor": {"category": "Genes & Molecular Entities", "sub_category": "Protein", "color": "#dc2626"},
    "fusion protein": {"category": "Genes & Molecular Entities", "sub_category": "Protein", "color": "#dc2626"},
    "fusion gene": {"category": "Genes & Molecular Entities", "sub_category": "Gene or Gene Product", "color": "#ef4444"},
    "gene fusion": {"category": "Genes & Molecular Entities", "sub_category": "Gene or Gene Product", "color": "#ef4444"},
    "complex": {"category": "Genes & Molecular Entities", "sub_category": "Protein", "color": "#dc2626"},
    "macromolecular complex": {"category": "Genes & Molecular Entities", "sub_category": "Protein", "color": "#dc2626"},
    "dna": {"category": "Genes & Molecular Entities", "sub_category": "Nucleic Acid", "color": "#991b1b"},
    "rna": {"category": "Genes & Molecular Entities", "sub_category": "Nucleic Acid", "color": "#991b1b"},
    "mrna": {"category": "Genes & Molecular Entities", "sub_category": "Nucleic Acid", "color": "#991b1b"},
    "microrna": {"category": "Genes & Molecular Entities", "sub_category": "Nucleic Acid", "color": "#991b1b"},
    "mirna": {"category": "Genes & Molecular Entities", "sub_category": "Nucleic Acid", "color": "#991b1b"},

    # 2. Chemicals & Drugs
    "chemical": {"category": "Chemicals & Drugs", "sub_category": "Chemical", "color": "#10b981"},
    "drug": {"category": "Chemicals & Drugs", "sub_category": "Drug", "color": "#059669"},
    "pharmacologic substance": {"category": "Chemicals & Drugs", "sub_category": "Pharmacologic Substance", "color": "#047857"},
    "toxic substance": {"category": "Chemicals & Drugs", "sub_category": "Toxic Substance", "color": "#065f46"},
    "substance": {"category": "Chemicals & Drugs", "sub_category": "Substance", "color": "#34d399"},
    "body fluid": {"category": "Chemicals & Drugs", "sub_category": "Body Fluid", "color": "#14b8a6"},
    "compound": {"category": "Chemicals & Drugs", "sub_category": "Chemical", "color": "#10b981"},
    "molecule": {"category": "Chemicals & Drugs", "sub_category": "Chemical", "color": "#10b981"},
    "small molecule": {"category": "Chemicals & Drugs", "sub_category": "Chemical", "color": "#10b981"},

    # 3. Diseases & Phenotypes
    "disease": {"category": "Diseases & Phenotypes", "sub_category": "Disease", "color": "#2563eb"},
    "syndrome": {"category": "Diseases & Phenotypes", "sub_category": "Syndrome", "color": "#1d4ed8"},
    "neoplasm": {"category": "Diseases & Phenotypes", "sub_category": "Neoplasm", "color": "#1e40af"},
    "cancer": {"category": "Diseases & Phenotypes", "sub_category": "Neoplasm", "color": "#1e40af"},
    "tumor": {"category": "Diseases & Phenotypes", "sub_category": "Neoplasm", "color": "#1e40af"},
    "pathologic function": {"category": "Diseases & Phenotypes", "sub_category": "Pathologic Function", "color": "#3b82f6"},
    "sign or symptom": {"category": "Diseases & Phenotypes", "sub_category": "Sign or Symptom", "color": "#f59e0b"},
    "symptom": {"category": "Diseases & Phenotypes", "sub_category": "Sign or Symptom", "color": "#f59e0b"},
    "phenotypic feature": {"category": "Diseases & Phenotypes", "sub_category": "Phenotypic Feature", "color": "#d97706"},
    "clinical finding": {"category": "Diseases & Phenotypes", "sub_category": "Clinical Finding", "color": "#b45309"},
    "disorder": {"category": "Diseases & Phenotypes", "sub_category": "Disease", "color": "#2563eb"},

    # 4. Biological Processes & Pathways
    "biological process": {"category": "Biological Processes & Pathways", "sub_category": "Biological Process", "color": "#8b5cf6"},
    "molecular function": {"category": "Biological Processes & Pathways", "sub_category": "Molecular Function", "color": "#7c3aed"},
    "pathway": {"category": "Biological Processes & Pathways", "sub_category": "Pathway", "color": "#6d28d9"},
    "metabolic process": {"category": "Biological Processes & Pathways", "sub_category": "Metabolic Process", "color": "#5b21b6"},
    "biologic function": {"category": "Biological Processes & Pathways", "sub_category": "Biologic Function", "color": "#a78bfa"},

    # 5. Anatomy & Cellular Entities
    "cell": {"category": "Anatomy & Cellular", "sub_category": "Cell", "color": "#ec4899"},
    "cellular component": {"category": "Anatomy & Cellular", "sub_category": "Cellular Component", "color": "#db2777"},
    "tissue": {"category": "Anatomy & Cellular", "sub_category": "Tissue", "color": "#0284c7"},
    "organ": {"category": "Anatomy & Cellular", "sub_category": "Organ", "color": "#0369a1"},
    "anatomical structure": {"category": "Anatomy & Cellular", "sub_category": "Anatomical Structure", "color": "#075985"},
    "anatomical entity": {"category": "Anatomy & Cellular", "sub_category": "Anatomical Entity", "color": "#38bdf8"},
    "anatomy": {"category": "Anatomy & Cellular", "sub_category": "Anatomical Entity", "color": "#38bdf8"},

    # 6. Organisms & Taxa
    "organism taxon": {"category": "Organisms & Taxa", "sub_category": "Organism Taxon", "color": "#16a34a"},
    "organism": {"category": "Organisms & Taxa", "sub_category": "Organism Taxon", "color": "#16a34a"},
    "virus": {"category": "Organisms & Taxa", "sub_category": "Virus", "color": "#15803d"},
    "bacterium": {"category": "Organisms & Taxa", "sub_category": "Bacterium", "color": "#166534"},

    # 7. Procedures & Methods
    "diagnostic procedure": {"category": "Procedures & Methods", "sub_category": "Diagnostic Procedure", "color": "#e11d48"},
    "therapeutic procedure": {"category": "Procedures & Methods", "sub_category": "Therapeutic Procedure", "color": "#be123c"},
    "laboratory procedure": {"category": "Procedures & Methods", "sub_category": "Laboratory Procedure", "color": "#9f1239"},
    "procedure": {"category": "Procedures & Methods", "sub_category": "Procedure", "color": "#fb7185"},

    # 8. Environmental & Fallbacks
    "environmental effect": {"category": "Environmental & Other", "sub_category": "Environmental Effect", "color": "#64748b"},
    "entity": {"category": "Environmental & Other", "sub_category": "General Entity", "color": "#475569"},
    "unknown": {"category": "Environmental & Other", "sub_category": "Unclassified", "color": "#94a3b8"},
}

def get_taxonomy_for_type(entity_type: str) -> Dict[str, str]:
    """
    Returns full category, sub_category, and standardized color for any given entity type.
    """
    t = str(entity_type).lower().strip()
    if t in TAXONOMY_MAP:
        return TAXONOMY_MAP[t]

    # Partial prefix/suffix fallback
    for k, tax in TAXONOMY_MAP.items():
        if k in t or t in k:
            return tax

    hex_digest = hashlib.md5(t.encode('utf-8')).hexdigest()
    return {
        "category": "Environmental & Other",
        "sub_category": "Unclassified",
        "color": f"#{hex_digest[:6]}"
    }

def get_color_for_type(entity_type: str) -> str:
    """
    Returns hex color code corresponding to the biomedical entity type.
    """
    return get_taxonomy_for_type(entity_type)["color"]

