from fastapi import FastAPI
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Proving AI Agents Are Ready for Production",
    version=settings.APP_VERSION,
)


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