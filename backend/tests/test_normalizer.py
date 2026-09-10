import pytest
from app.services.normalizer_service import (
    normalize_entities_non_llm,
    clean_morphology,
    lemmatize_biomedical_entity,
    get_scispacy_large
)

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
