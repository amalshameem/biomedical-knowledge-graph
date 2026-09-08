import io
import csv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.sql_models import Project
from app.services.export_service import generate_project_export_bundle, generate_graphml_string

router = APIRouter()

@router.get("/{project_id}/export")
def export_bundle(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    triples_data = [
        {
            "entity1": t.entity1,
            "entity1_type": t.entity1_type,
            "relationship": t.relationship_name,
            "entity2": t.entity2,
            "entity2_type": t.entity2_type,
            "evidence": t.evidence or "",
            "pubmed_ids": t.pubmed_ids or ""
        }
        for t in project.triples
    ]

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

    csv_out = io.StringIO()
    writer = csv.writer(csv_out)
    writer.writerow(["entity1", "entity1_type", "relationship", "entity2", "entity2_type", "evidence", "pubmed_ids"])
    for t in project.triples:
        writer.writerow([
            t.entity1,
            t.entity1_type,
            t.relationship_name,
            t.entity2,
            t.entity2_type,
            t.evidence or "",
            t.pubmed_ids or ""
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

    triples_data = [
        {
            "entity1": t.entity1,
            "entity1_type": t.entity1_type,
            "relationship": t.relationship_name,
            "entity2": t.entity2,
            "entity2_type": t.entity2_type,
            "evidence": t.evidence or "",
            "pubmed_ids": t.pubmed_ids or ""
        }
        for t in project.triples
    ]

    graphml_xml = generate_graphml_string(triples_data)
    filename = f"{project.name.replace(' ', '_')}_graph.graphml"
    return Response(
        content=graphml_xml,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
