from fastapi import FastAPI
from app.api.router import router as api_router
from app.workers.proactive_worker import ProactiveEmailWorker
from app.services.ai_service import AIService
from app.integrations.email.gmail import GmailProvider # Example
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="AI Email Assistant API")

app.include_router(api_router, prefix="/api/v1")

# Global worker instance
worker: ProactiveEmailWorker = None

@app.on_event("startup")
async def startup_event():
    global worker
    # Use environment variables for security
    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    provider = GmailProvider(credentials_json=creds_path) 
    ai_service = AIService(email_provider=provider)
    worker = ProactiveEmailWorker(email_provider=provider, ai_service=ai_service)
    
    # Start the worker in the background
    asyncio.create_task(worker.monitor_inbox())

@app.post("/worker/stop")
async def stop_worker():
    if worker:
        worker.stop()
        return {"message": "Worker stopped"}
    return {"message": "Worker not running"}

@app.get("/")
async def root():
    return {"message": "Welcome to the AI Email Assistant API"}
