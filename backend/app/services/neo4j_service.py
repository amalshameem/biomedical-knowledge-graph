import logging
from typing import List, Dict, Any, Optional
from app.core.database import neo4j_conn
from app.services.ner_service import get_color_for_type, get_taxonomy_for_type, get_relationship_color

logger = logging.getLogger(__name__)

def sync_triples_to_neo4j(project_id: str, triples: List[Dict[str, Any]], ner_mode: str = "advanced") -> bool:
    """
    Writes triples into Neo4j with nodes labeled by Entity and typed directed relationships.
    Stores category, sub_category, color, evidence, pubmed_ids, and project_id as properties.
    """
    driver = neo4j_conn.get_driver()
    if not driver:
        logger.warning("Neo4j driver unavailable; skipping graph persistence.")
        return False

    cypher_query = """
    UNWIND $triples AS row
    MERGE (e1:Entity {name: row.entity1, project_id: $project_id})
    ON CREATE SET 
        e1.canonical_name = row.entity1,
        e1.type = row.entity1_type,
        e1.category = row.category1,
        e1.sub_category = row.sub_category1,
        e1.color = row.color1,
        e1.created_at = datetime()
    ON MATCH SET
        e1.type = row.entity1_type,
        e1.category = row.category1,
        e1.sub_category = row.sub_category1,
        e1.color = row.color1

    MERGE (e2:Entity {name: row.entity2, project_id: $project_id})
    ON CREATE SET 
        e2.canonical_name = row.entity2,
        e2.type = row.entity2_type,
        e2.category = row.category2,
        e2.sub_category = row.sub_category2,
        e2.color = row.color2,
        e2.created_at = datetime()
    ON MATCH SET
        e2.type = row.entity2_type,
        e2.category = row.category2,
        e2.sub_category = row.sub_category2,
        e2.color = row.color2

    MERGE (e1)-[r:RELATION {relationship: row.relationship, project_id: $project_id}]->(e2)
    SET 
        r.evidence = row.evidence,
        r.pubmed_ids = row.pubmed_ids,
        r.updated_at = datetime()
    """

    payload = []
    for t in triples:
        e1 = t.get("entity1", "").strip()
        e2 = t.get("entity2", "").strip()
        rel = t.get("relationship", "").strip()
        if not e1 or not e2 or not rel:
            continue
        type1 = t.get("entity1_type", "Unknown")
        type2 = t.get("entity2_type", "Unknown")
        tax1 = get_taxonomy_for_type(type1, ner_mode=ner_mode)
        tax2 = get_taxonomy_for_type(type2, ner_mode=ner_mode)

        payload.append({
            "entity1": e1,
            "entity1_type": type1,
            "category1": tax1["category"],
            "sub_category1": tax1["sub_category"],
            "color1": tax1["color"],
            "relationship": rel,
            "entity2": e2,
            "entity2_type": type2,
            "category2": tax2["category"],
            "sub_category2": tax2["sub_category"],
            "color2": tax2["color"],
            "evidence": t.get("evidence", ""),
            "pubmed_ids": t.get("pubmed_ids", "")
        })

    try:
        with driver.session() as session:
            session.run(cypher_query, project_id=project_id, triples=payload)
        logger.info(f"Successfully synced {len(payload)} triples to Neo4j for project {project_id}")
        return True
    except Exception as e:
        logger.error(f"Neo4j sync error: {e}")
        return False

def delete_project_from_neo4j(project_id: str) -> bool:
    """
    Deletes all nodes and relationships associated with a project in Neo4j.
    """
    driver = neo4j_conn.get_driver()
    if not driver:
        return False
    try:
        with driver.session() as session:
            session.run("MATCH (n {project_id: $project_id}) DETACH DELETE n", project_id=project_id)
        logger.info(f"Deleted Neo4j graph elements for project {project_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to delete Neo4j elements for project {project_id}: {e}")
        return False

def get_cytoscape_graph(project_id: str, min_connections: int = 1, entity_type: Optional[str] = None, ner_mode: str = "advanced") -> Dict[str, Any]:
    """
    Queries Neo4j (or returns formatted JSON) for Cytoscape.js rendering with categories and subcategories.
    """
    nodes_map: Dict[str, Dict[str, Any]] = {}
    edges_list: List[Dict[str, Any]] = []

    driver = neo4j_conn.get_driver()
    if driver:
        try:
            with driver.session() as session:
                query = """
                MATCH (e1:Entity {project_id: $project_id})-[r:RELATION {project_id: $project_id}]->(e2:Entity {project_id: $project_id})
                RETURN e1.name AS e1_name, e1.type AS e1_type, e1.category AS e1_category, e1.sub_category AS e1_sub_category, e1.color AS e1_color,
                       r.relationship AS rel, r.evidence AS evidence, r.pubmed_ids AS pubmed_ids,
                       e2.name AS e2_name, e2.type AS e2_type, e2.category AS e2_category, e2.sub_category AS e2_sub_category, e2.color AS e2_color
                """
                results = session.run(query, project_id=project_id)
                for record in results:
                    e1_name = record["e1_name"]
                    e2_name = record["e2_name"]
                    rel = record["rel"]

                    tax1 = get_taxonomy_for_type(record["e1_type"] or "Unknown", ner_mode=ner_mode)
                    tax2 = get_taxonomy_for_type(record["e2_type"] or "Unknown", ner_mode=ner_mode)

                    if e1_name not in nodes_map:
                        nodes_map[e1_name] = {
                            "id": e1_name,
                            "label": e1_name,
                            "type": record["e1_type"] or "Unknown",
                            "category": tax1["category"] if ner_mode == "basic" else (record.get("e1_category") or tax1["category"]),
                            "sub_category": tax1["sub_category"] if ner_mode == "basic" else (record.get("e1_sub_category") or tax1["sub_category"]),
                            "color": tax1["color"] if ner_mode == "basic" else (record.get("e1_color") or tax1["color"]),
                            "degree": 0
                        }
                    nodes_map[e1_name]["degree"] += 1

                    if e2_name not in nodes_map:
                        nodes_map[e2_name] = {
                            "id": e2_name,
                            "label": e2_name,
                            "type": record["e2_type"] or "Unknown",
                            "category": tax2["category"] if ner_mode == "basic" else (record.get("e2_category") or tax2["category"]),
                            "sub_category": tax2["sub_category"] if ner_mode == "basic" else (record.get("e2_sub_category") or tax2["sub_category"]),
                            "color": tax2["color"] if ner_mode == "basic" else (record.get("e2_color") or tax2["color"]),
                            "degree": 0
                        }
                    nodes_map[e2_name]["degree"] += 1

                    edge_id = f"{e1_name}_{rel}_{e2_name}"
                    edges_list.append({
                        "data": {
                            "id": edge_id,
                            "source": e1_name,
                            "target": e2_name,
                            "label": rel.replace("_", " "),
                            "relationship": rel,
                            "color": get_relationship_color(rel),
                            "evidence": record["evidence"] or "",
                            "pubmed_ids": record["pubmed_ids"] or ""
                        }
                    })
        except Exception as e:
            logger.error(f"Neo4j query error: {e}")

    # Degree and type filtering
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
                t = n_data["type"]
                cat = n_data.get("category", "Environmental & Other")
                subcat = n_data.get("sub_category", t)
                types_count[t] = types_count.get(t, 0) + 1
                categories_count[cat] = categories_count.get(cat, 0) + 1
                subcategories_count[subcat] = subcategories_count.get(subcat, 0) + 1

    filtered_edges = [
        e for e in edges_list
        if e["data"]["source"] in valid_node_ids and e["data"]["target"] in valid_node_ids
    ]

    return {
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
