import uvicorn
from fastapi import FastAPI
from app.api.agent_router import router as agent_router

app = FastAPI(title="Multimodal Real Estate AI Agent", version="1.0")

# Nhúng router của Agent vào FastAPI app chính
app.include_router(agent_router, prefix="/api/v1/agent", tags=["Agent"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Multimodal Real Estate AI Agent API"}

if __name__ == "__main__":
    uvicorn.run("main_agent:app", host="0.0.0.0", port=8000, reload=True)
