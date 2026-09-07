import asyncio
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes.chat import router as api_router
from app.integrations.email.gmail import GmailProvider
from app.services.email_agent import AIService
from app.workers.inbox_monitor import ProactiveEmailWorker

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.worker = None
    app.state.worker_task = None
    if os.getenv("ENABLE_PROACTIVE_WORKER", "false").lower() == "true":
        provider = GmailProvider(os.getenv("GMAIL_CREDENTIALS_PATH", "token.json"))
        await provider.authenticate()
        worker = ProactiveEmailWorker(provider, AIService(provider))
        app.state.worker = worker
        app.state.worker_task = asyncio.create_task(worker.monitor_inbox())
    yield
    if app.state.worker:
        app.state.worker.stop()
    if app.state.worker_task:
        app.state.worker_task.cancel()
        try:
            await app.state.worker_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="AI Email Assistant API", lifespan=lifespan)


@app.middleware("http")
async def add_timeout_middleware(request: Request, call_next):
    try:
        return await asyncio.wait_for(call_next(request), timeout=30.0)
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"detail": "Request timed out after 30 seconds"})


app.include_router(api_router, prefix="/api/v1")


@app.post("/worker/stop")
async def stop_worker(request: Request):
    worker = getattr(request.app.state, "worker", None)
    if not worker:
        return {"message": "Worker is not running"}
    worker.stop()
    return {"message": "Worker stopped"}


@app.get("/")
async def root():
    return {"message": "Welcome to the AI Email Assistant API"}
