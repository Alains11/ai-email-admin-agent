import msal
import requests
import asyncio
from app.integrations.email.base import EmailProvider, EmailMessage
from typing import List, Optional

class OutlookProvider(EmailProvider):
    def __init__(self, client_id: str, tenant_id: str):
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.access_token = None

    async def authenticate(self):
        # Use PublicClientApplication for delegated permissions (User context)
        if not self.client_id or not self.tenant_id:
            raise ValueError("Outlook client_id and tenant_id are required")
        app = msal.PublicClientApplication(
            self.client_id, authority=f"https://login.microsoftonline.com/{self.tenant_id}"
        )

        # Try to get token from cache first
        accounts = app.get_accounts()
        if accounts:
            result = app.acquire_token_silent(scopes=["https://graph.microsoft.com/Mail.ReadWrite"], account=accounts[0])
        else:
            # Fallback to device flow for non-interactive environments
            flow = app.initiate_device_flow(scopes=["https://graph.microsoft.com/Mail.ReadWrite"])
            print(f"Please go to {flow['verification_uri']} and enter code: {flow['user_code']}")
            result = await asyncio.to_thread(app.acquire_token_by_device_flow, flow)

        self.access_token = result.get("access_token") if result else None
        if not self.access_token:
            raise RuntimeError(result.get("error_description", "Outlook authentication failed"))

    async def _request(self, method: str, endpoint: str, **kwargs):
        if not self.access_token:
            raise RuntimeError("Outlook provider is not authenticated")
        headers = {"Authorization": f"Bearer {self.access_token}", **kwargs.pop("headers", {})}
        response = await asyncio.to_thread(requests.request, method, endpoint, headers=headers, timeout=20, **kwargs)
        response.raise_for_status()
        return response

    async def fetch_emails(self, query: Optional[str] = None, limit: int = 10) -> List[EmailMessage]:
        endpoint = f"https://graph.microsoft.com/v1.0/me/messages"
        params = {'$top': limit}
        if query:
            params['$filter'] = f"contains(subject, '{query}')"
            
        response = (await self._request("GET", endpoint, params=params)).json()
        
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
        endpoint = "https://graph.microsoft.com/v1.0/me/sendMail"
        await self._request("POST", endpoint, json={
            "message": {
                "subject": subject,
                "body": {"contentType": "Text", "content": body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            }
        })

    async def draft_email(self, to: str, subject: str, body: str) -> str:
        endpoint = "https://graph.microsoft.com/v1.0/me/messages"
        response = await self._request("POST", endpoint, json={
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": to}}],
        })
        return response.json()["id"]

    async def update_label(self, email_id: str, label: str, action: str = "add"):
        message = (await self._request(
            "GET", f"https://graph.microsoft.com/v1.0/me/messages/{email_id}?$select=categories"
        )).json()
        categories = set(message.get("categories") or [])
        if action == "add":
            categories.add(label)
        else:
            categories.discard(label)
        await self._request(
            "PATCH",
            f"https://graph.microsoft.com/v1.0/me/messages/{email_id}",
            json={"categories": sorted(categories)},
        )
