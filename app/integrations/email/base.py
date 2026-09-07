from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel

class EmailMessage(BaseModel):
    id: str
    subject: str
    sender: str
    body: str
    date: str
    labels: List[str] = []

class EmailProvider(ABC):
    @abstractmethod
    async def authenticate(self):
        """Handle authentication for the provider."""
        pass

    @abstractmethod
    async def fetch_emails(self, query: Optional[str] = None, limit: int = 10) -> List[EmailMessage]:
        """Fetch emails based on a query."""
        pass

    @abstractmethod
    async def send_email(self, to: str, subject: str, body: str):
        """Send an email."""
        pass

    @abstractmethod
    async def draft_email(self, to: str, subject: str, body: str) -> str:
        """Create a draft email and return the draft ID."""
        pass

    @abstractmethod
    async def update_label(self, email_id: str, label: str, action: str = "add"):
        """Add or remove a label from an email."""
        pass
