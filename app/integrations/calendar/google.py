from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.integrations.calendar.base import CalendarProvider, CalendarEvent
from datetime import datetime
from typing import List

class GoogleCalendarProvider(CalendarProvider):
    def __init__(self, credentials_json: str):
        self.credentials_json = credentials_json
        self.service = None

    async def authenticate(self):
        creds = Credentials.from_authorized_user_file(self.credentials_json)
        self.service = build('calendar', 'v3', credentials=creds)

    async def create_event(self, event: CalendarEvent) -> str:
        event_body = {
            'summary': event.summary,
            'description': event.description,
            'start': {'dateTime': event.start_time.isoformat(), 'timeZone': 'UTC'},
            'end': {'dateTime': event.end_time.isoformat(), 'timeZone': 'UTC'},
            'location': event.location,
        }
        created_event = self.service.events().insert(calendarId='primary', body=event_body).execute()
        return created_event.get('id')

    async def list_events(self, start_time: datetime, end_time: datetime) -> List[CalendarEvent]:
        events_result = self.service.events().list(
            calendarId='primary', 
            timeMin=start_time.isoformat() + 'Z', 
            timeMax=end_time.isoformat() + 'Z', 
            singleEvents=True, 
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        return [
            CalendarEvent(
                id=e.get('id'),
                summary=e.get('summary', 'No Title'),
                description=e.get('description'),
                start_time=datetime.fromisoformat(e['start'].get('dateTime')),
                end_time=datetime.fromisoformat(e['end'].get('dateTime')),
                location=e.get('location')
            ) for e in events
        ]

    async def delete_event(self, event_id: str):
        self.service.events().delete(calendarId='primary', eventId=event_id).execute()
