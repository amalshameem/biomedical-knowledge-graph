import os
import shutil
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import UPLOAD_DIR
from app.models.sql_models import Project, Document, Triple
from app.models.domain import ProjectCreate, ProjectResponse, ProjectDetail, DocumentInfo, TripleItem
from app.services.neo4j_service import delete_project_from_neo4j

router = APIRouter()

@router.get("", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    results = []
    for p in projects:
        resp = ProjectResponse.model_validate(p)
        resp.documents_count = len(p.documents)
        results.append(resp)
    return results

@router.post("", response_model=ProjectResponse)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    ner_mode = (payload.ner_mode or "advanced").lower().strip()
    if ner_mode not in ("basic", "advanced"):
        ner_mode = "advanced"

    project = Project(
        name=payload.name,
        description=payload.description,
        status="created",
        ner_mode=ner_mode
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    resp = ProjectResponse.model_validate(project)
    resp.documents_count = 0
    return resp

@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    docs = [
        DocumentInfo(
            id=d.id,
            filename=d.filename,
            file_size=d.file_size,
            chunks_count=d.chunks_count,
            created_at=d.created_at
        ) for d in project.documents
    ]

    triples = [
        TripleItem(
            id=t.id,
            entity1=t.entity1,
            entity1_type=t.entity1_type,
            relationship=t.relationship_name,
            entity2=t.entity2,
            entity2_type=t.entity2_type,
            evidence=t.evidence or "",
            pubmed_ids=t.pubmed_ids or ""
        ) for t in project.triples
    ]

    resp = ProjectDetail(
        id=project.id,
        name=project.name,
        description=project.description or "",
        status=project.status,
        provider=project.provider,
        model=project.model,
        ner_mode=project.ner_mode or "advanced",
        total_chunks=project.total_chunks,
        total_triples=project.total_triples,
        execution_time=project.execution_time,
        created_at=project.created_at,
        updated_at=project.updated_at,
        documents_count=len(docs),
        documents=docs,
        triples=triples
    )
    return resp

@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clean up files on disk
    project_upload_dir = UPLOAD_DIR / project_id
    if project_upload_dir.exists():
        shutil.rmtree(project_upload_dir, ignore_errors=True)

    # Clean up Neo4j graph nodes and relations
    delete_project_from_neo4j(project_id)

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully", "id": project_id}

@router.post("/{project_id}/documents", response_model=List[DocumentInfo])
async def upload_documents(project_id: str, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_dir = UPLOAD_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)

    saved_docs = []
    for file in files:
        if not file.filename:
            continue
        clean_name = os.path.basename(file.filename.replace("\\", "/"))
        if not clean_name.lower().endswith(".pdf"):
            continue

        file_path = project_dir / clean_name
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        doc = Document(
            project_id=project_id,
            filename=clean_name,
            file_path=str(file_path),
            file_size=len(content)
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)


        saved_docs.append(DocumentInfo(
            id=doc.id,
            filename=doc.filename,
            file_size=doc.file_size,
            chunks_count=0,
            created_at=doc.created_at
        ))

    if not saved_docs:
        raise HTTPException(status_code=400, detail="No valid PDF documents were uploaded. Please upload at least one .pdf file.")

    return saved_docs

