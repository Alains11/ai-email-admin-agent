from fastapi import APIRouter, Depends
from app.api.schemas import ChatRequest, ChatResponse
from app.services.ai_service import AIService
from app.integrations.email.gmail import GmailProvider
from app.integrations.email.outlook import OutlookProvider
from app.integrations.email.yahoo import YahooProvider

router = APIRouter()

def get_provider(request: ChatRequest):
    if request.provider == "gmail":
        return GmailProvider(credentials_json=request.credentials.get("path"))
    elif request.provider == "outlook":
        return OutlookProvider(
            client_id=request.credentials.get("client_id"),
            client_secret=request.credentials.get("client_secret"),
            tenant_id=request.credentials.get("tenant_id")
        )
    elif request.provider == "yahoo":
        return YahooProvider(
            email_user=request.credentials.get("user"),
            password=request.credentials.get("password")
        )
    raise ValueError("Unsupported provider")

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    provider = get_provider(request)
    await provider.authenticate()
    
    ai_service = AIService(provider)
    response_text = await ai_service.process_request(request.message, request.history)
    
    return ChatResponse(response=response_text)

@router.get("/status")
async def get_status():
    return {"status": "online", "version": "0.1.0"}
