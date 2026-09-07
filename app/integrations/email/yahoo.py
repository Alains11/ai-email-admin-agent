import imaplib
import smtplib
import email
import asyncio
from email.utils import formatdate
from email.mime.text import MIMEText
from app.integrations.email.base import EmailProvider, EmailMessage
from typing import List, Optional

class YahooProvider(EmailProvider):
    def __init__(self, email_user: str, password: str):
        self.email_user = email_user
        self.password = password
        self.imap_conn = None
        self.smtp_conn = None

    async def authenticate(self):
        if not self.email_user or not self.password:
            raise ValueError("Yahoo user and app password are required")
        self.imap_conn = await asyncio.to_thread(imaplib.IMAP4_SSL, "imap.mail.yahoo.com")
        await asyncio.to_thread(self.imap_conn.login, self.email_user, self.password)
        self.smtp_conn = await asyncio.to_thread(smtplib.SMTP_SSL, "smtp.mail.yahoo.com", 465)
        await asyncio.to_thread(self.smtp_conn.login, self.email_user, self.password)

    async def fetch_emails(self, query: Optional[str] = None, limit: int = 10) -> List[EmailMessage]:
        if not self.imap_conn:
            raise RuntimeError("Yahoo provider is not authenticated")
        status, _ = await asyncio.to_thread(self.imap_conn.select, "inbox")
        if status != "OK":
            raise RuntimeError("Could not select the Yahoo inbox")

        # IMAP search requires specific syntax. If query is None, use "ALL".
        # If query is provided, we wrap it in quotes to avoid "BAD" errors for complex strings.
        search_query = "ALL" if not query else f'TEXT "{query}"'
        status, messages = await asyncio.to_thread(self.imap_conn.search, None, search_query)
        if status != "OK":
            raise RuntimeError("Yahoo email search failed")
        
        email_ids = messages[0].split()[-limit:]
        email_list = []

        
        for e_id in email_ids:
            res, msg_data = await asyncio.to_thread(self.imap_conn.fetch, e_id, "(RFC822)")
            if res != "OK":
                continue
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Safely extract body
                    body = self._get_body(msg)
                        
                    email_list.append(EmailMessage(
                        id=str(e_id),
                        subject=msg['subject'] or "No Subject",
                        sender=msg['from'] or "Unknown",
                        body=body,
                        date=msg['date'] or "",
                    ))
        return email_list

    @staticmethod
    def _get_body(msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain" and not part.get_filename():
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
            return "No content"
        payload = msg.get_payload(decode=True)
        return payload.decode(msg.get_content_charset() or "utf-8", errors="ignore") if payload else "No content"

    async def send_email(self, to: str, subject: str, body: str):
        if not self.smtp_conn:
            raise RuntimeError("Yahoo provider is not authenticated")
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.email_user
        msg['To'] = to
        await asyncio.to_thread(self.smtp_conn.send_message, msg)

    async def draft_email(self, to: str, subject: str, body: str) -> str:
        if not self.imap_conn:
            raise RuntimeError("Yahoo provider is not authenticated")
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = self.email_user
        msg["To"] = to
        msg["Date"] = formatdate(localtime=True)
        status, _ = await asyncio.to_thread(
            self.imap_conn.append, "Drafts", "\\Draft", None, msg.as_bytes()
        )
        if status != "OK":
            raise RuntimeError("Could not save the Yahoo draft")
        return "yahoo-draft"

    async def update_label(self, email_id: str, label: str, action: str = "add"):
        raise NotImplementedError(
            "Yahoo IMAP does not expose Gmail-style labels; use folders in Yahoo Mail instead."
        )
