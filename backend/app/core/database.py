import logging
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from neo4j import GraphDatabase, Driver
from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Setup
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Neo4j Driver Manager
class Neo4jConnection:
    def __init__(self):
        self._driver: Optional[Driver] = None

    def get_driver(self, uri: str = None, user: str = None, password: str = None) -> Optional[Driver]:
        target_uri = uri or settings.NEO4J_URI
        target_user = user or settings.NEO4J_USER
        target_pwd = password or settings.NEO4J_PASSWORD
        
        try:
            if not self._driver:
                self._driver = GraphDatabase.driver(
                    target_uri,
                    auth=(target_user, target_pwd),
                    max_connection_lifetime=3600
                )
            return self._driver
        except Exception as e:
            logger.warning(f"Neo4j connection could not be established: {e}")
            return None

    def close(self):
        if self._driver:
            self._driver.close()
            self._driver = None

neo4j_conn = Neo4jConnection()
