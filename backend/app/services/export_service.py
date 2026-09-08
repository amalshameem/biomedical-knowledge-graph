import io
import csv
import json
import zipfile
import datetime
import networkx as nx
from typing import List, Dict, Any, Tuple

def generate_graphml_string(triples: List[Dict[str, Any]]) -> str:
    """
    Converts triples to a standard GraphML XML string with evidence and PubMed IDs.
    """
    G = nx.DiGraph()
    for r in triples:
        e1 = r.get("entity1", "").strip()
        t1 = r.get("entity1_type", "Unknown").strip()
        rel = r.get("relationship", "").strip()
        e2 = r.get("entity2", "").strip()
        t2 = r.get("entity2_type", "Unknown").strip()
        evidence = str(r.get("evidence", ""))
        pmids = str(r.get("pubmed_ids", ""))

        if not e1 or not e2 or not rel:
            continue

        if not G.has_node(e1):
            G.add_node(e1, label=e1, type=t1)
        if not G.has_node(e2):
            G.add_node(e2, label=e2, type=t2)

        G.add_edge(e1, e2, label=rel, evidence=evidence, pubmed_ids=pmids)

    bio = io.BytesIO()
    nx.write_graphml(G, bio, encoding='utf-8', prettyprint=True)
    return bio.getvalue().decode('utf-8')

def generate_project_export_bundle(project_name: str, provider: str, model_name: str, triples: List[Dict[str, Any]], execution_time: float = 0.0, files_processed: List[str] = None) -> bytes:
    """
    Generates a full ZIP export bundle containing combined CSV with evidence, GraphML, metadata JSON, and README.
    """
    zip_buffer = io.BytesIO()
    timestamp_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        # 1. Metadata JSON
        metadata = {
            "project_name": project_name,
            "export_timestamp": timestamp_str,
            "llm_provider": provider,
            "model": model_name,
            "execution_time_seconds": execution_time,
            "total_triples": len(triples),
            "files_processed": files_processed or [],
            "triples": triples
        }
        zip_file.writestr("metadata.json", json.dumps(metadata, indent=2))

        # 2. Combined CSV with Evidence
        csv_out = io.StringIO()
        writer = csv.writer(csv_out)
        writer.writerow(["entity1", "entity1_type", "relationship", "entity2", "entity2_type", "evidence", "pubmed_ids"])
        for t in triples:
            writer.writerow([
                t.get("entity1", ""),
                t.get("entity1_type", "Unknown"),
                t.get("relationship", ""),
                t.get("entity2", ""),
                t.get("entity2_type", "Unknown"),
                t.get("evidence", ""),
                t.get("pubmed_ids", "")
            ])
        zip_file.writestr(f"{project_name}_triples.csv", csv_out.getvalue())

        # 3. Combined GraphML
        graphml_str = generate_graphml_string(triples)
        zip_file.writestr(f"{project_name}_knowledge_graph.graphml", graphml_str)

        # 4. README
        readme_content = f"""Biomedical Knowledge Graph Export Bundle
=========================================
Project Name: {project_name}
Export Timestamp: {timestamp_str}
LLM Provider: {provider}
Model: {model_name}
Total Extracted Triples: {len(triples)}
Execution Time: {execution_time:.2f} seconds
Files Processed: {', '.join(files_processed or [])}

Files in this bundle:
- README.txt: This description file.
- metadata.json: Run configuration, metrics, and structured triples JSON.
- {project_name}_triples.csv: All extracted triples with ontology types, evidence sentences, and PubMed IDs.
- {project_name}_knowledge_graph.graphml: Standard GraphML file importable into Cytoscape, Gephi, or NetworkX.
"""
        zip_file.writestr("README.txt", readme_content)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()
