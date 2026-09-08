import os
import time
import logging
from typing import Optional
from Bio import Entrez
from app.core.config import settings

logger = logging.getLogger(__name__)

Entrez.email = settings.ENTREZ_EMAIL
if settings.ENTREZ_API_KEY:
    Entrez.api_key = settings.ENTREZ_API_KEY

def fetch_pubmed_ids_for_triple(entity1: str, entity2: str, max_results: int = 3, email: Optional[str] = None, api_key: Optional[str] = None) -> str:
    """
    Queries NCBI PubMed for articles mentioning both entity1 and entity2.
    Respects NCBI rate limits (3 req/sec unauthenticated, 10 req/sec with key).
    """
    if not entity1 or not entity2:
        return "Unknown"

    if email:
        Entrez.email = email
    if api_key:
        Entrez.api_key = api_key

    query = f'"{entity1}"[Title/Abstract] AND "{entity2}"[Title/Abstract]'

    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        handle.close()

        # Respect NCBI rate limits
        delay = 0.1 if Entrez.api_key else 0.35
        time.sleep(delay)

        id_list = record.get("IdList", [])
        if id_list:
            return ";".join(id_list)
        return "No match found"
    except Exception as e:
        logger.warning(f"Entrez search error for '{entity1}' & '{entity2}': {e}")
        time.sleep(0.5)
        return "Error"
