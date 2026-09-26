from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Veridyn Test Agent")


class AgentRequest(BaseModel):
    input: str


class AgentResponse(BaseModel):
    output: str


@app.post("/agent", response_model=AgentResponse)
def run_agent(request: AgentRequest):
    return AgentResponse(
        output=f"Hello! I received your message: {request.input}"
    )


@app.get("/health")
def health():
    return {"status": "ok"}
