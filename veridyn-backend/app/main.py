from fastapi import FastAPI

app = FastAPI(
    title="Veridyn",
    description="Proving AI Agents Are Ready for Production",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "message": "Veridyn backend is running",
        "status": "ok",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }