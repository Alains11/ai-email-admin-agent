"""Chat API routes."""

import os

from fastapi import APIRouter, HTTPException
from app.api.models.chat import ChatRequest, ChatResponse
from app.services.email_agent import AIService
from app.integrations.email.gmail import GmailProvider
from app.integrations.email.outlook import OutlookProvider
from app.integrations.email.yahoo import YahooProvider

router = APIRouter()

def get_provider(request: ChatRequest):
    if request.provider == "gmail":
        path = request.credentials.get("path") or os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
        return GmailProvider(credentials_json=str(path))
    elif request.provider == "outlook":
        return OutlookProvider(
            client_id=str(request.credentials.get("client_id") or os.getenv("OUTLOOK_CLIENT_ID", "")),
            tenant_id=str(request.credentials.get("tenant_id") or os.getenv("OUTLOOK_TENANT_ID", ""))
        )
    elif request.provider == "yahoo":
        return YahooProvider(
            email_user=str(request.credentials.get("user") or os.getenv("YAHOO_USER", "")),
            password=str(request.credentials.get("password") or os.getenv("YAHOO_PASSWORD", ""))
        )
    raise HTTPException(status_code=422, detail="Unsupported provider")

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        provider = get_provider(request)
        await provider.authenticate()
        ai_service = AIService(provider, session_id=request.session_id)
        history = [message.model_dump() for message in request.history]
        response_text = await ai_service.process_request(request.message, history)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Email provider error: {exc}") from exc
    
    return ChatResponse(response=response_text)

@router.get("/status")
async def get_status():
    return {"status": "online", "version": "0.1.0"}
