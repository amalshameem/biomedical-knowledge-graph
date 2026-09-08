import os
import zipfile
import io
import pytest
from app.services.pdf_service import extract_text_from_pdf
from app.services.export_service import generate_project_export_bundle, generate_graphml_string

def test_pdf_extraction_with_benchmark():
    pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "sample_data", "biomedical_benchmark_corpus.pdf")
    if not os.path.exists(pdf_path):
        pdf_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "biomedical_benchmark_corpus.pdf")
    if not os.path.exists(pdf_path):
        pytest.skip(f"Benchmark file not found")

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    chunks = extract_text_from_pdf(pdf_bytes, filename="28214071.pdf")
    assert len(chunks) > 0
    # Verify that first chunk has substantial biomedical text
    assert len(chunks[0]) > 50

def test_export_bundle_generation():
    triples = [
        {
            "entity1": "LCN2",
            "entity1_type": "Gene or Gene Product",
            "relationship": "associated_with",
            "entity2": "Inflammatory Bowel Disease",
            "entity2_type": "Disease",
            "evidence": "Lipocalin-2 expression is markedly upregulated in mucosal biopsies from patients with IBD.",
            "pubmed_ids": "28214071;29180292"
        },
        {
            "entity1": "Infliximab",
            "entity1_type": "Drug",
            "relationship": "treats",
            "entity2": "Crohn's Disease",
            "entity2_type": "Disease",
            "evidence": "Anti-TNF therapy with infliximab induces endoscopic mucosal healing in Crohn's disease.",
            "pubmed_ids": "15671120"
        }
    ]

    zip_bytes = generate_project_export_bundle(
        project_name="Test_IBD_Study",
        provider="LM Studio",
        model_name="biomed-qwen-7b",
        triples=triples,
        execution_time=12.4,
        files_processed=["28214071.pdf"]
    )

    assert len(zip_bytes) > 0
    # Read back the ZIP in-memory
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        filenames = z.namelist()
        assert "metadata.json" in filenames
        assert "Test_IBD_Study_triples.csv" in filenames
        assert "Test_IBD_Study_knowledge_graph.graphml" in filenames
        assert "README.txt" in filenames

def test_clean_and_defragment_text():
    from app.services.pdf_service import clean_and_defragment_text

    raw_sample = "Lipocalin-\n2 (LCN2) promotes in  fl a  mmation in in-\nterleukin-6 stimulated macrophages [1, 2] as shown previously (Smith et al., 2020)."
    cleaned = clean_and_defragment_text(raw_sample)

    assert "Lipocalin-2" in cleaned
    assert "inflammation" in cleaned
    assert "interleukin-6" in cleaned
    assert "[1, 2]" not in cleaned
    assert "Smith et al." not in cleaned
    assert "macrophages" in cleaned

    raw_input = "This 25-kDa secretory glycoprotein was initially identi fiedand puri fiedfrom neutrophil granules and is encoded byagene located at chromosome locus 9q34.11."
    cleaned = clean_and_defragment_text(raw_input)
    assert "identified and purified from" in cleaned
    assert "encoded by a gene" in cleaned
    assert "25-kDa" in cleaned
    assert "9q34.11" in cleaned

    # Test line wrap & biological entity preservation
    wrap_input = "The inter-\nleukin-6 gene is up-\nregulated in cells, and Lipocalin-\n2 was isolated."
    cleaned_wrap = clean_and_defragment_text(wrap_input)
    assert "interleukin-6" in cleaned_wrap
    assert "upregulated" in cleaned_wrap
    assert "Lipocalin-2" in cleaned_wrap

    # Test glued keywords & split ligatures
    complex_input = "activationof the LCN2gene leads to proli feration, in flammation, and am pli fication."
    cleaned_complex = clean_and_defragment_text(complex_input)
    assert "activation of" in cleaned_complex
    assert "LCN2 gene" in cleaned_complex
    assert "proliferation" in cleaned_complex
    assert "inflammation" in cleaned_complex
    assert "amplification" in cleaned_complex

def test_embedded_cleaner_service():
    from app.services.embedded_cleaner_service import EmbeddedCleanerService

    raw_input = "This 25-kDa secretory glycoprotein was initially identi fiedand puri fiedfrom neutrophil granules and is encoded byagene located at chromosome locus 9q34.11."
    cleaned = EmbeddedCleanerService.clean_text_embedded(raw_input)
    assert "identified" in cleaned
    assert "purified" in cleaned
    assert "25-kDa" in cleaned
    assert "9q34.11" in cleaned
