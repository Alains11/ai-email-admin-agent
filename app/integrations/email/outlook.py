import msal
import requests
from app.integrations.email.base import EmailProvider, EmailMessage
from typing import List, Optional

class OutlookProvider(EmailProvider):
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token = None

    async def authenticate(self):
        app = msal.ConfidentialClientApplication(
            self.client_id, authority=f"https://login.microsoftonline.com/{self.tenant_id}",
            client_credential=self.client_secret
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        self.access_token = result.get("access_token")

    async def fetch_emails(self, query: Optional[str] = None, limit: int = 10) -> List[EmailMessage]:
        headers = {'Authorization': f'Bearer {self.access_token}'}
        endpoint = f"https://graph.microsoft.com/v1.0/me/messages"
        params = {'$top': limit}
        if query:
            params['$filter'] = f"contains(subject, '{query}')"
            
        response = requests.get(endpoint, headers=headers, params=params).json()
        
        email_list = []
        for msg in response.get('value', []):
            email_list.append(EmailMessage(
                id=msg['id'],
                subject=msg['subject'],
                sender=msg['from']['emailAddress']['address'],
                body=msg['bodyPreview'],
                date=msg['receivedDateTime'],
            ))
        return email_list

    async def send_email(self, to: str, subject: str, body: str):
        # Implementation for sending email via Graph API
        pass

    async def draft_email(self, to: str, subject: str, body: str) -> str:
        # Implementation for creating draft via Graph API
        return "outlook_draft_id"

    async def update_label(self, email_id: str, label: str, action: str = "add"):
        # Implementation for updating categories via Graph API
        pass
