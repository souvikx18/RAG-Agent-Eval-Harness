from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.api.auth import router as auth_router
from app.api.agents import router as agents_router
from app.api.agent_versions import router as agent_versions_router
from app.api.evaluations import router as evaluations_router
from app.api.test_cases import router as test_cases_router
from app.api.test_runs import router as test_runs_router
from app.api.execution_traces import router as execution_traces_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Proving AI Agents Are Ready for Production",
    version=settings.APP_VERSION,
)

app.include_router(auth_router)
app.include_router(agents_router)
app.include_router(agent_versions_router)
app.include_router(evaluations_router)
app.include_router(test_cases_router)
app.include_router(test_runs_router)
app.include_router(execution_traces_router)

@app.get("/")
def root():
    return {
        "message": f"{settings.APP_NAME} backend is running",
        "environment": settings.ENVIRONMENT,
        "status": "ok",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/health/database")
def database_health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))

    return {
        "database": "connected",
        "status": "healthy",
    }

