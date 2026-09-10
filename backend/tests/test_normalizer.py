import pytest
from app.services.normalizer_service import (
    normalize_entities_non_llm,
    clean_morphology,
    lemmatize_biomedical_entity,
    get_scispacy_large
)
from app.services.ner_service import snap_entity_to_gliner_spans

def test_clean_morphology():
    assert clean_morphology("TNF-α") == "TNF-alpha"
    assert clean_morphology("macrophages") == "macrophage"
    assert clean_morphology("antibodies") == "antibody"
    assert clean_morphology("IL - 10") == "IL-10"

def test_biomedical_dictionary_mapping():
    entities = {"Lipocalin-2", "NGAL", "tumor necrosis factor-alpha", "p53", "crohn's disease", "dss"}
    context = "Lipocalin-2 (LCN2) is an innate immune protein."
    mapping = normalize_entities_non_llm(entities, context)
    
    assert mapping["Lipocalin-2"] == "LCN2"
    assert mapping["NGAL"] == "LCN2"
    assert mapping["tumor necrosis factor-alpha"] == "TNF"
    assert mapping["p53"] == "TP53"
    assert mapping["crohn's disease"] == "Crohn's Disease"
    assert mapping["dss"] == "Dextran Sulfate Sodium"

def test_rapidfuzz_clustering():
    entities = {"lipocalin-2 protein", "lipocalin-2 proteins"}
    mapping = normalize_entities_non_llm(entities)
    # Both should map to the canonical singular form
    assert mapping["lipocalin-2 protein"] == mapping["lipocalin-2 proteins"]

def test_scispacy_large_integration():
    nlp = get_scispacy_large()
    assert nlp is not None
    assert "abbreviation_detector" in nlp.pipe_names

def test_scispacy_abbreviation_and_lemmatization():
    context = "Neutrophil gelatinase-associated lipocalin (NGAL) levels rise after acute kidney injury (AKI)."
    entities = {"NGAL", "AKI", "acute kidney injuries"}
    mapping = normalize_entities_non_llm(entities, context)
    
    assert mapping["NGAL"] == "LCN2"
    assert mapping["AKI"] == "Acute Kidney Injury"
    assert mapping["acute kidney injuries"] == "Acute Kidney Injury"

def test_snap_entity_to_gliner_spans():
    gliner_candidates = [
        {"text": "LCN2", "type": "Gene or Gene Product", "score": 0.95},
        {"text": "IL-6", "type": "Gene or Gene Product", "score": 0.92},
        {"text": "ulcerative colitis", "type": "Disease", "score": 0.98},
    ]

    # Safe specifier snapping: "LCN2 gene" -> "LCN2"
    snapped, t = snap_entity_to_gliner_spans("LCN2 gene", gliner_candidates)
    assert snapped == "LCN2"
    assert t == "Gene or Gene Product"

    # Safe specifier snapping: "serum LCN2 levels" -> "LCN2"
    snapped, t = snap_entity_to_gliner_spans("serum LCN2 levels", gliner_candidates)
    assert snapped == "LCN2"

    # Protected modifier preservation: "IL-6 receptor" -> preserved as distinct receptor entity
    snapped, t = snap_entity_to_gliner_spans("IL-6 receptor", gliner_candidates)
    assert snapped == "IL-6 receptor"
    assert t == "Receptor"

def test_gliner_ner_extraction():
    from app.services.ner_service import extract_entities_detailed, get_taxonomy_for_type
    sample_text = "TNF-alpha stimulates interleukin-6 and causes rheumatoid arthritis."
    entities = extract_entities_detailed(sample_text)
    assert len(entities) > 0
    ner_type = entities[0]["type"]

    tax = get_taxonomy_for_type(ner_type)
    assert "category" in tax
    assert "sub_category" in tax
    assert tax["color"].startswith("#")

def test_relationship_colors():
    from app.services.ner_service import get_relationship_color, RELATIONSHIP_COLORS
    for rel in ["treats", "causes", "predisposes", "positively_regulates", "negatively_regulates", "interacts_with", "associated_with", "expressed_in", "coexists_with"]:
        color = get_relationship_color(rel)
        assert color.startswith("#")
        assert len(color) == 7
