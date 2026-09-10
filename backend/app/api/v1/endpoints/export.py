import io
import csv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.sql_models import Project
from app.services.export_service import generate_project_export_bundle, generate_graphml_string

router = APIRouter()

SYMMETRIC_RELATIONS = {"associated_with", "interacts_with", "coexists_with"}

def get_deduped_triples_for_export(project) -> list:
    seen = set()
    cleaned = []
    for t in project.triples:
        e1 = (t.entity1 or "").strip()
        e2 = (t.entity2 or "").strip()
        rel = (t.relationship_name or "").lower().strip()
        if not e1 or not e2 or e1.lower() == e2.lower():
            continue
        if rel in SYMMETRIC_RELATIONS:
            pair_key = tuple(sorted([e1.lower(), e2.lower()]))
            key = (pair_key, rel)
        else:
            key = (e1.lower(), rel, e2.lower())
        if key not in seen:
            seen.add(key)
            cleaned.append({
                "entity1": t.entity1,
                "entity1_type": t.entity1_type,
                "relationship": t.relationship_name,
                "entity2": t.entity2,
                "entity2_type": t.entity2_type,
                "evidence": t.evidence or "",
                "pubmed_ids": t.pubmed_ids or ""
            })
    return cleaned

@router.get("/{project_id}/export")
def export_bundle(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    triples_data = get_deduped_triples_for_export(project)
    files_processed = [d.filename for d in project.documents]

    zip_bytes = generate_project_export_bundle(
        project_name=project.name.replace(" ", "_"),
        provider=project.provider or "Unknown",
        model_name=project.model or "Unknown",
        triples=triples_data,
        execution_time=project.execution_time,
        files_processed=files_processed
    )

    filename = f"{project.name.replace(' ', '_')}_export.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{project_id}/export/csv")
def export_csv(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    triples_data = get_deduped_triples_for_export(project)
    csv_out = io.StringIO()
    writer = csv.writer(csv_out)
    writer.writerow(["entity1", "entity1_type", "relationship", "entity2", "entity2_type", "evidence", "pubmed_ids"])
    for t in triples_data:
        writer.writerow([
            t["entity1"],
            t["entity1_type"],
            t["relationship"],
            t["entity2"],
            t["entity2_type"],
            t["evidence"],
            t["pubmed_ids"]
        ])

    filename = f"{project.name.replace(' ', '_')}_triples.csv"
    return Response(
        content=csv_out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{project_id}/export/graphml")
def export_graphml(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    triples_data = get_deduped_triples_for_export(project)
    graphml_xml = generate_graphml_string(triples_data)
    filename = f"{project.name.replace(' ', '_')}_graph.graphml"
    return Response(
        content=graphml_xml,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
