import re
import logging
from typing import Dict, Set, List, Tuple, Optional
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

# Greek symbol map
GREEK_MAP = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta",
    "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
    "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu",
    "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi",
    "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega"
}

# Curated Gold Standard Biomedical Synonym / Alias Dictionary (HGNC / MeSH / ChEMBL / DOID)
BIOMEDICAL_CANONICAL_DICT = {
    # Proteins & Genes (HGNC)
    "lipocalin-2": "LCN2",
    "lipocalin 2": "LCN2",
    "lcn-2": "LCN2",
    "ngal": "LCN2",
    "siderocalin": "LCN2",
    "24p3": "LCN2",
    "24p3r": "24p3R",
    "neutrophil gelatinase-associated lipocalin": "LCN2",
    "tumor necrosis factor": "TNF",
    "tumor necrosis factor-alpha": "TNF",
    "tumor necrosis factor alpha": "TNF",
    "tnf-alpha": "TNF",
    "tnf-a": "TNF",
    "tnf a": "TNF",
    "tnfa": "TNF",
    "interleukin-1 alpha": "IL1A",
    "interleukin-1alpha": "IL1A",
    "interleukin 1 alpha": "IL1A",
    "il-1 alpha": "IL1A",
    "il-1alpha": "IL1A",
    "il-1a": "IL1A",
    "il-1 a": "IL1A",
    "il1a": "IL1A",
    "interleukin-1 beta": "IL1B",
    "interleukin-1beta": "IL1B",
    "interleukin 1 beta": "IL1B",
    "il-1 beta": "IL1B",
    "il-1b": "IL1B",
    "il-1 b": "IL1B",
    "il1b": "IL1B",
    "interleukin-6": "IL6",
    "interleukin 6": "IL6",
    "il-6": "IL6",
    "il6": "IL6",
    "interleukin-8": "IL8",
    "interleukin 8": "IL8",
    "il-8": "IL8",
    "il8": "IL8",
    "cxcl8": "IL8",
    "interleukin-10": "IL10",
    "interleukin 10": "IL10",
    "il-10": "IL10",
    "il-10-knockout": "IL10",
    "il10": "IL10",
    "interleukin-17a": "IL17A",
    "interleukin 17a": "IL17A",
    "il-17a": "IL17A",
    "il-17 a": "IL17A",
    "il17a": "IL17A",
    "interleukin-17f": "IL17F",
    "interleukin 17f": "IL17F",
    "il-17f": "IL17F",
    "il-17 f": "IL17F",
    "il17f": "IL17F",
    "interleukin-22": "IL22",
    "interleukin 22": "IL22",
    "il-22": "IL22",
    "il22": "IL22",
    "interleukin-23": "IL23A",
    "interleukin 23": "IL23A",
    "il-23": "IL23A",
    "il23": "IL23A",
    "il-23p19": "IL23A",
    "il-23p40": "IL23A",
    "interferon-gamma": "IFNG",
    "interferon gamma": "IFNG",
    "ifn-gamma": "IFNG",
    "ifn-g": "IFNG",
    "ifng": "IFNG",
    "nf-kappa b": "NFKB1",
    "nf-kappab": "NFKB1",
    "nf-kb": "NFKB1",
    "nfkb": "NFKB1",
    "nfkb1": "NFKB1",
    "stat-1": "STAT1",
    "stat1": "STAT1",
    "stat-3": "STAT3",
    "stat3": "STAT3",
    "cxcr-2": "CXCR2",
    "cxcr2": "CXCR2",
    "c-x-c motif receptor 2": "CXCR2",
    "erk1/2": "ERK",
    "erk": "ERK",
    "lrp-2": "LRP2",
    "lrp2": "LRP2",
    "cd11c": "CD11c",
    "transformation related protein 53": "TP53",
    "cellular tumor antigen p53": "TP53",
    "p53": "TP53",
    "tp53": "TP53",
    "epidermal growth factor receptor": "EGFR",
    "egfr": "EGFR",
    "vascular endothelial growth factor a": "VEGFA",
    "vegf-a": "VEGFA",
    "vegfa": "VEGFA",
    "vegf": "VEGFA",

    # Cells
    "macrophages": "Macrophage",
    "macrophage": "Macrophage",
    "neutrophils": "Neutrophil",
    "neutrophil": "Neutrophil",
    "t cells": "T Cell",
    "t cell": "T Cell",
    "t-lymphocytes": "T Cell",
    "t lymphocytes": "T Cell",
    "t lymphocyte": "T Cell",
    "b cells": "B Cell",
    "b cell": "B Cell",
    "dendritic cells": "Dendritic Cell",
    "dendritic cell": "Dendritic Cell",
    "epithelial cells": "Epithelial Cell",
    "epithelial cell": "Epithelial Cell",
    "hepatocytes": "Hepatocyte",
    "hepatocyte": "Hepatocyte",
    "chondrocytes": "Chondrocyte",
    "chondrocyte": "Chondrocyte",
    "adipocytes": "Adipocyte",
    "adipocyte": "Adipocyte",
    "keratinocytes": "Keratinocyte",
    "keratinocyte": "Keratinocyte",

    # Diseases (MeSH / DOID)
    "inflammatory bowel disease": "Inflammatory Bowel Disease",
    "inflammatory bowel diseases": "Inflammatory Bowel Disease",
    "ibd": "Inflammatory Bowel Disease",
    "crohn's disease": "Crohn's Disease",
    "crohns disease": "Crohn's Disease",
    "crohn disease": "Crohn's Disease",
    "cd": "Crohn's Disease",
    "ulcerative colitis": "Ulcerative Colitis",
    "uc": "Ulcerative Colitis",
    "colitis": "Colitis",
    "nonalcoholic steatohepatitis": "Nonalcoholic Steatohepatitis",
    "nash": "Nonalcoholic Steatohepatitis",
    "alcoholic steatohepatitis": "Alcoholic Steatohepatitis",
    "ash": "Alcoholic Steatohepatitis",
    "acute-on-chronic liver failure": "Acute-on-Chronic Liver Failure",
    "acute on chronic liver failure": "Acute-on-Chronic Liver Failure",
    "aclf": "Acute-on-Chronic Liver Failure",
    "type 1 diabetes mellitus": "Type 1 Diabetes Mellitus",
    "type 1 diabetes": "Type 1 Diabetes Mellitus",
    "t1dm": "Type 1 Diabetes Mellitus",
    "latent autoimmune diabetes in adults": "Latent Autoimmune Diabetes in Adults",
    "latent autoimmune diabetes": "Latent Autoimmune Diabetes in Adults",
    "lada": "Latent Autoimmune Diabetes in Adults",
    "gestational diabetes": "Gestational Diabetes",
    "gestational diabetes mellitus": "Gestational Diabetes",
    "gdm": "Gestational Diabetes",
    "type 2 diabetes mellitus": "Type 2 Diabetes Mellitus",
    "type 2 diabetes": "Type 2 Diabetes Mellitus",
    "t2dm": "Type 2 Diabetes Mellitus",
    "diabetes mellitus": "Diabetes Mellitus",
    "diabetes": "Diabetes Mellitus",
    "coronary artery disease": "Coronary Artery Disease",
    "cad": "Coronary Artery Disease",
    "acute kidney injury": "Acute Kidney Injury",
    "aki": "Acute Kidney Injury",
    "chronic kidney disease": "Chronic Kidney Disease",
    "ckd": "Chronic Kidney Disease",
    "colorectal cancer": "Colorectal Cancer",
    "colorectal carcinoma": "Colorectal Cancer",
    "crc": "Colorectal Cancer",
    "rheumatoid arthritis": "Rheumatoid Arthritis",
    "ra": "Rheumatoid Arthritis",
    "multiple sclerosis": "Multiple Sclerosis",
    "ms": "Multiple Sclerosis",
    "psoriasis": "Psoriasis",
    "obesity": "Obesity",
    "atherosclerosis": "Atherosclerosis",
    "arteriosclerosis": "Arteriosclerosis",

    # Chemicals & Drugs (ChEMBL / RxNorm)
    "lipopolysaccharide": "Lipopolysaccharide",
    "lps": "Lipopolysaccharide",
    "endotoxin": "Endotoxin",
    "dextran sulfate sodium": "Dextran Sulfate Sodium",
    "dextran sodium sulfate": "Dextran Sulfate Sodium",
    "dss": "Dextran Sulfate Sodium",
    "dexamethasone": "Dexamethasone",
    "rosiglitazone": "Rosiglitazone",
    "infliximab": "Infliximab",
    "remicade": "Infliximab",
    "adalimumab": "Adalimumab",
    "humira": "Adalimumab",
    "azathioprine": "Azathioprine",
    "5-aminosalicylic acid": "Mesalamine",
    "mesalazine": "Mesalamine",
    "mesalamine": "Mesalamine",
    "5-asa": "Mesalamine",
}

PROTECTED_MEDICAL_NOUNS = {
    "diabetes", "feces", "sepsis", "cirrhosis", "sclerosis", "psoriasis",
    "herpes", "rabies", "mumps", "measles", "fetus", "status", "species",
    "mucus", "pelvis", "bronchus", "thrombus", "metastasis", "paralysis",
    "syphilis", "tuberculosis", "fibrosis", "necrosis", "stenosis", "thrombosis",
    "atherosclerosis", "arteriosclerosis", "steatohepatitis"
}

_scispacy_nlp = None


def get_scispacy_large():
    """
    Lazy-load ScispaCy Large (en_core_sci_lg) singleton with AbbreviationDetector.
    Falls back gracefully to None if model or package is not available.
    """
    global _scispacy_nlp
    if _scispacy_nlp is not None:
        return _scispacy_nlp

    try:
        import spacy
        from scispacy.abbreviation import AbbreviationDetector

        # Disable 'ner' to save memory & compute (GLiNER handles NER)
        nlp = spacy.load("en_core_sci_lg", disable=["ner"])
        if "abbreviation_detector" not in nlp.pipe_names:
            nlp.add_pipe("abbreviation_detector")
        _scispacy_nlp = nlp
        logger.info("Successfully loaded ScispaCy Large (en_core_sci_lg) with AbbreviationDetector.")
    except Exception as e:
        logger.warning(f"Could not load ScispaCy Large (en_core_sci_lg): {e}. Falling back to heuristic normalization.")
        _scispacy_nlp = None

    return _scispacy_nlp


def clean_morphology(text: str) -> str:
    """
    Cleans punctuation, Greek letters, and standardizes spacing without LLM.
    Safely preserves medical nouns ending in 's' (e.g. diabetes, feces, sepsis).
    """
    if not text:
        return ""

    s = text.strip()

    # Transliterate Greek symbols
    for greek_char, latin_name in GREEK_MAP.items():
        s = s.replace(greek_char, latin_name)
        s = s.replace(greek_char.upper(), latin_name.capitalize())

    # Plural cleanup for common biomedical endings (safely protecting medical nouns)
    lower = s.lower()
    last_word = lower.split()[-1] if lower.split() else ""
    if last_word not in PROTECTED_MEDICAL_NOUNS and lower not in PROTECTED_MEDICAL_NOUNS:
        if lower.endswith("ies") and len(lower) > 5:
            s = s[:-3] + "y"
        elif lower.endswith("es") and not lower.endswith("ses") and not lower.endswith("tes") and not lower.endswith("ces") and len(lower) > 5:
            s = s[:-2] + "e"
        elif lower.endswith("s") and not lower.endswith("ss") and not lower.endswith("us") and not lower.endswith("is") and not lower.endswith("as") and not lower.endswith("os") and len(lower) > 4:
            s = s[:-1]

    # Normalize hyphens and internal whitespace
    s = re.sub(r'[\u2010\u2011\u2012\u2013\u2014\u2015]', '-', s)
    s = re.sub(r'\s*-\s*', '-', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def lemmatize_biomedical_entity(text: str) -> str:
    """
    Uses ScispaCy Large to lemmatize biomedical phrases (e.g. 'macrophages' -> 'macrophage',
    'antibodies' -> 'antibody', 'acute kidney injuries' -> 'acute kidney injury'),
    while strictly protecting medical nouns (e.g. diabetes, sepsis, cirrhosis).
    """
    if not text:
        return ""

    cleaned = clean_morphology(text)
    lower = cleaned.lower()
    last_word = lower.split()[-1] if lower.split() else ""
    if lower in PROTECTED_MEDICAL_NOUNS or last_word in PROTECTED_MEDICAL_NOUNS:
        return cleaned

    nlp = get_scispacy_large()
    if nlp is None:
        return cleaned

    try:
        doc = nlp(cleaned)
        lemmatized_tokens = []
        for token in doc:
            tok_lower = token.text.lower()
            if tok_lower in PROTECTED_MEDICAL_NOUNS:
                lemmatized_tokens.append(token.text)
            else:
                lemmatized_tokens.append(token.lemma_)
        result = " ".join(lemmatized_tokens).strip()
        # Clean any spaces around hyphens introduced by tokenization
        result = re.sub(r'\s*-\s*', '-', result)
        return result if result else cleaned
    except Exception:
        return cleaned


def extract_intra_doc_abbreviations(text_corpus: str) -> Dict[str, str]:
    """
    Finds abbreviations defined in document text using ScispaCy AbbreviationDetector,
    with regex fallback / supplement.
    Maps:
      short_form.lower() -> long_form
      long_form.lower() -> short_form
    """
    abbr_map = {}
    if not text_corpus:
        return abbr_map

    # 1. ScispaCy AbbreviationDetector (parses document context with syntactic accuracy)
    nlp = get_scispacy_large()
    if nlp is not None:
        try:
            # Process up to 200,000 characters to ensure responsive performance
            sample = text_corpus[:200000]
            doc = nlp(sample)
            for abrv in getattr(doc._, "abbreviations", []):
                short_form = abrv.text.strip()
                long_form = getattr(abrv._, "long_form", None)
                long_text = long_form.text.strip() if long_form is not None else ""
                if short_form and long_text and len(long_text) > len(short_form):
                    if short_form.lower() not in {"and", "the", "for", "with"}:
                        abbr_map[short_form.lower()] = long_text
                        abbr_map[long_text.lower()] = short_form
        except Exception as e:
            logger.warning(f"ScispaCy abbreviation detector encountered warning: {e}")

    # 2. Regex fallback and supplementary pattern matcher
    # Pattern: Long Form (SHORT_FORM) e.g. "Inflammatory Bowel Disease (IBD)"
    pattern = re.compile(r'([A-Za-z0-9\-\s]{3,50})\s*\(([A-Za-z0-9\-]{2,12})\)')
    for match in pattern.finditer(text_corpus):
        long_form = match.group(1).strip()
        short_form = match.group(2).strip()
        if len(long_form) > len(short_form) and short_form.lower() not in {"and", "the", "for", "with"}:
            if short_form.lower() not in abbr_map:
                abbr_map[short_form.lower()] = long_form
            if long_form.lower() not in abbr_map:
                abbr_map[long_form.lower()] = short_form

    return abbr_map


def normalize_entities_non_llm(entities: Set[str], text_context: str = "") -> Dict[str, str]:
    """
    Deterministic, fast non-LLM normalizer for biomedical entities:
    1. ScispaCy Large Abbreviation mapping + regex fallback
    2. Curated gold-standard dictionary lookup (HGNC, MeSH, ChEMBL, DOID)
    3. ScispaCy Large lemmatization and biomedical morphology cleaning
    4. Intra-document RapidFuzz string clustering (>= 92% similarity)
    """
    if not entities:
        return {}

    mapping: Dict[str, str] = {}
    doc_abbreviations = extract_intra_doc_abbreviations(text_context)

    # Step 1: Dictionary & Abbreviation Resolution with ScispaCy Lemmatization
    intermediate: Dict[str, str] = {}
    for ent in entities:
        if not ent or not ent.strip():
            continue
        raw_ent = ent.strip()
        ent_lower = raw_ent.lower()

        # Check dictionary directly
        if ent_lower in BIOMEDICAL_CANONICAL_DICT:
            intermediate[raw_ent] = BIOMEDICAL_CANONICAL_DICT[ent_lower]
            continue

        # Check doc-level abbreviation
        if ent_lower in doc_abbreviations:
            expanded = doc_abbreviations[ent_lower]
            exp_lower = expanded.lower()
            if exp_lower in BIOMEDICAL_CANONICAL_DICT:
                intermediate[raw_ent] = BIOMEDICAL_CANONICAL_DICT[exp_lower]
                continue
            # If expanded long form has a canonical format, use it
            intermediate[raw_ent] = expanded
            continue

        # ScispaCy Large biomedical lemmatization & morphological normalization
        lemmatized = lemmatize_biomedical_entity(raw_ent)
        lem_lower = lemmatized.lower()
        if lem_lower in BIOMEDICAL_CANONICAL_DICT:
            intermediate[raw_ent] = BIOMEDICAL_CANONICAL_DICT[lem_lower]
            continue

        if lem_lower in doc_abbreviations:
            expanded = doc_abbreviations[lem_lower]
            exp_lower = expanded.lower()
            if exp_lower in BIOMEDICAL_CANONICAL_DICT:
                intermediate[raw_ent] = BIOMEDICAL_CANONICAL_DICT[exp_lower]
                continue
            intermediate[raw_ent] = expanded
            continue

        # Clean morphology fallback
        cleaned = clean_morphology(raw_ent)
        clean_lower = cleaned.lower()
        if clean_lower in BIOMEDICAL_CANONICAL_DICT:
            intermediate[raw_ent] = BIOMEDICAL_CANONICAL_DICT[clean_lower]
            continue

        intermediate[raw_ent] = lemmatized if lemmatized else cleaned

    # Step 2: RapidFuzz clustering on remaining entities within the document
    unique_canons = list(set(intermediate.values()))
    alias_clusters: Dict[str, str] = {}

    for i in range(len(unique_canons)):
        e1 = unique_canons[i]
        for j in range(i + 1, len(unique_canons)):
            e2 = unique_canons[j]
            ratio = fuzz.ratio(e1.lower(), e2.lower())
            if ratio >= 92:
                # Merge into the shorter/canonical representation
                preferred = e1 if len(e1) <= len(e2) else e2
                subordinate = e2 if preferred == e1 else e1
                alias_clusters[subordinate] = preferred

    # Final mapping assembly
    for raw_ent, norm in intermediate.items():
        final_name = alias_clusters.get(norm, norm)
        mapping[raw_ent] = final_name

    return mapping
