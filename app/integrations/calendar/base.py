from abc import ABC, abstractmethod
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class CalendarEvent(BaseModel):
    id: Optional[str] = None
    summary: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None

class CalendarProvider(ABC):
    @abstractmethod
    async def authenticate(self):
        """Handle authentication for the calendar provider."""
        pass

    @abstractmethod
    async def create_event(self, event: CalendarEvent) -> str:
        """Create a new calendar event and return the event ID."""
        pass

    @abstractmethod
    async def list_events(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        """List events within a time range."""
        pass

    @abstractmethod
    async def delete_event(self, event_id: str):
        """Delete a calendar event."""
        pass
