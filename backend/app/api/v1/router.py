from fastapi import APIRouter
from app.api.v1.endpoints import projects, extraction, graph, llm, export, settings

api_router = APIRouter()
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(extraction.router, prefix="/projects", tags=["extraction"])
api_router.include_router(graph.router, prefix="/projects", tags=["graph"])
api_router.include_router(export.router, prefix="/projects", tags=["export"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
