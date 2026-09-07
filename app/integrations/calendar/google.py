import asyncio
from datetime import datetime, timezone
from typing import List

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from app.integrations.calendar.base import CalendarProvider, CalendarEvent

class GoogleCalendarProvider(CalendarProvider):
    def __init__(self, credentials_json: str):
        self.credentials_json = credentials_json
        self.service = None

    async def authenticate(self):
        creds = await asyncio.to_thread(
            Credentials.from_authorized_user_file, self.credentials_json
        )
        self.service = await asyncio.to_thread(build, 'calendar', 'v3', credentials=creds)

    @staticmethod
    def _rfc3339(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')

    async def create_event(self, event: CalendarEvent) -> str:
        event_body = {
            'summary': event.summary,
            'description': event.description,
            'start': {'dateTime': self._rfc3339(event.start_time), 'timeZone': 'UTC'},
            'end': {'dateTime': self._rfc3339(event.end_time), 'timeZone': 'UTC'},
            'location': event.location,
        }
        if not self.service:
            raise RuntimeError("Google Calendar provider is not authenticated")
        request = self.service.events().insert(calendarId='primary', body=event_body)
        created_event = await asyncio.to_thread(request.execute)
        return created_event.get('id')

    async def list_events(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        if not self.service:
            raise RuntimeError("Google Calendar provider is not authenticated")
        request = self.service.events().list(
            calendarId='primary',
            timeMin=self._rfc3339(start_time),
            timeMax=self._rfc3339(end_time),
            singleEvents=True,
            orderBy='startTime'
        )
        events_result = await asyncio.to_thread(request.execute)
        
        events = events_result.get('items', [])
        calendar_events = []
        for event in events:
            start = event['start'].get('dateTime') or event['start'].get('date')
            end = event['end'].get('dateTime') or event['end'].get('date')
            if not start or not end:
                continue
            calendar_events.append(CalendarEvent(
                id=event.get('id'),
                summary=event.get('summary', 'No Title'),
                description=event.get('description'),
                start_time=datetime.fromisoformat(start),
                end_time=datetime.fromisoformat(end),
                location=event.get('location')
            ))
        return calendar_events

    async def delete_event(self, event_id: str):
        if not self.service:
            raise RuntimeError("Google Calendar provider is not authenticated")
        request = self.service.events().delete(calendarId='primary', eventId=event_id)
        await asyncio.to_thread(request.execute)
