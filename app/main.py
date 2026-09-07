from fastapi import FastAPI
from app.api.router import router as api_router

app = FastAPI(title="AI Email Assistant API")

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Email Assistant API"}
