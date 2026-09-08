from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.sql_models import Project, Triple
from app.models.domain import CytoscapeGraph
from app.services.neo4j_service import get_cytoscape_graph
from app.services.ner_service import get_color_for_type, get_taxonomy_for_type, get_relationship_color

router = APIRouter()

@router.get("/{project_id}/graph", response_model=CytoscapeGraph)
def fetch_graph(
    project_id: str,
    min_connections: int = Query(1, ge=1, le=20),
    entity_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # 1. Try querying Neo4j
    graph_data = get_cytoscape_graph(project_id, min_connections=min_connections, entity_type=entity_type)
    
    # 2. Fallback to SQLite triples if Neo4j is empty / disconnected
    if not graph_data["elements"]["nodes"] and project.triples:
        nodes_map = {}
        edges_list = []

        for t in project.triples:
            e1 = t.entity1.strip()
            e2 = t.entity2.strip()
            rel = t.relationship_name.strip()
            t1 = t.entity1_type or "Unknown"
            t2 = t.entity2_type or "Unknown"
            tax1 = get_taxonomy_for_type(t1)
            tax2 = get_taxonomy_for_type(t2)

            if not e1 or not e2:
                continue

            if e1 not in nodes_map:
                nodes_map[e1] = {
                    "id": e1,
                    "label": e1,
                    "type": t1,
                    "category": tax1["category"],
                    "sub_category": tax1["sub_category"],
                    "color": tax1["color"],
                    "degree": 0
                }
            nodes_map[e1]["degree"] += 1

            if e2 not in nodes_map:
                nodes_map[e2] = {
                    "id": e2,
                    "label": e2,
                    "type": t2,
                    "category": tax2["category"],
                    "sub_category": tax2["sub_category"],
                    "color": tax2["color"],
                    "degree": 0
                }
            nodes_map[e2]["degree"] += 1

            edges_list.append({
                "data": {
                    "id": f"{e1}_{rel}_{e2}_{t.id[:6]}",
                    "source": e1,
                    "target": e2,
                    "label": rel.replace("_", " "),
                    "relationship": rel,
                    "color": get_relationship_color(rel),
                    "evidence": t.evidence or "",
                    "pubmed_ids": t.pubmed_ids or ""
                }
            })

        # Apply filters
        filtered_nodes = []
        types_count: Dict[str, int] = {}
        categories_count: Dict[str, int] = {}
        subcategories_count: Dict[str, int] = {}
        valid_node_ids = set()

        for n_id, n_data in nodes_map.items():
            if n_data["degree"] >= min_connections:
                if not entity_type or entity_type.lower() == "all" or n_data["type"].lower() == entity_type.lower():
                    valid_node_ids.add(n_id)
                    filtered_nodes.append({"data": n_data})
                    t_name = n_data["type"]
                    cat_name = n_data["category"]
                    subcat_name = n_data["sub_category"]
                    types_count[t_name] = types_count.get(t_name, 0) + 1
                    categories_count[cat_name] = categories_count.get(cat_name, 0) + 1
                    subcategories_count[subcat_name] = subcategories_count.get(subcat_name, 0) + 1

        filtered_edges = [
            e for e in edges_list
            if e["data"]["source"] in valid_node_ids and e["data"]["target"] in valid_node_ids
        ]

        graph_data = {
            "elements": {
                "nodes": filtered_nodes,
                "edges": filtered_edges
            },
            "stats": {
                "total_nodes": len(filtered_nodes),
                "total_edges": len(filtered_edges),
                "types_count": types_count,
                "categories_count": categories_count,
                "subcategories_count": subcategories_count
            }
        }

    return graph_data
