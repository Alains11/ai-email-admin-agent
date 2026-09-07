"""Tests for the email agent service."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.email_agent import AIService
from app.integrations.email.base import EmailProvider, EmailMessage

@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=EmailProvider)
    provider.fetch_emails = AsyncMock(return_value=[
        EmailMessage(id="1", subject="Test Email", sender="test@example.com", body="Hello world", date="2026-09-06")
    ])
    provider.send_email = AsyncMock()
    provider.draft_email = AsyncMock(return_value="draft_123")
    provider.update_label = AsyncMock()
    return provider

@pytest.mark.asyncio
async def test_ai_service_fetch_emails(mock_provider):
    ai_service = AIService(email_provider=mock_provider)
    response = await ai_service.process_request("Fetch my emails")
    
    mock_provider.fetch_emails.assert_called()
    assert "Test Email" in response or "emails" in response.lower()

@pytest.mark.asyncio
async def test_ai_service_draft_reply(mock_provider):
    ai_service = AIService(email_provider=mock_provider)
    response = await ai_service.process_request("Draft a reply to email 1 saying I am interested")
    
    mock_provider.draft_email.assert_called()
    assert "draft" in response.lower()
