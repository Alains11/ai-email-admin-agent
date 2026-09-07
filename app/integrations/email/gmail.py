import base64
import asyncio
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.integrations.email.base import EmailProvider, EmailMessage
from typing import List, Optional

class GmailProvider(EmailProvider):

    def __init__(self, credentials_json: str):
        self.credentials_json = credentials_json
        self.service = None

    async def authenticate(self):
        creds = await asyncio.to_thread(
            Credentials.from_authorized_user_file, self.credentials_json
        )
        self.service = await asyncio.to_thread(build, 'gmail', 'v1', credentials=creds)

    async def fetch_emails(self, query: Optional[str] = None, limit: int = 10) -> List[EmailMessage]:
        if not self.service:
            raise RuntimeError("Gmail provider is not authenticated")
        request = self.service.users().messages().list(userId='me', q=query, maxResults=limit)
        results = await asyncio.to_thread(request.execute)
        messages = results.get('messages', [])

        email_list = []
        for msg in messages:
            request = self.service.users().messages().get(userId='me', id=msg['id'])
            detail = await asyncio.to_thread(request.execute)
            headers = detail['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            
            email_list.append(EmailMessage(
                id=msg['id'],
                subject=subject,
                sender=sender,
                body=detail.get('snippet', ''),
                date=next((h['value'] for h in headers if h['name'] == 'Date'), ''),
            ))
        return email_list

    async def send_email(self, to: str, subject: str, body: str):
        if not self.service:
            raise RuntimeError("Gmail provider is not authenticated")
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        request = self.service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        )
        await asyncio.to_thread(request.execute)

    async def draft_email(self, to: str, subject: str, body: str) -> str:
        if not self.service:
            raise RuntimeError("Gmail provider is not authenticated")
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        request = self.service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw_message}}
        )
        result = await asyncio.to_thread(request.execute)
        return result['id']

    async def update_label(self, email_id: str, label: str, action: str = "add"):
        if not self.service:
            raise RuntimeError("Gmail provider is not authenticated")
        # Gmail labels are managed via modify
        # Note: label must exist in Gmail or this will fail
        body = {
            'addLabelIds': [label] if action == "add" else [],
            'removeLabelIds': [label] if action == "remove" else []
        }
        request = self.service.users().messages().modify(
            userId='me',
            id=email_id,
            body=body
        )
        await asyncio.to_thread(request.execute)
