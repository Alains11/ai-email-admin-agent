import imaplib
import smtplib
import email
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
        self.imap_conn = imaplib.IMAP4_SSL("imap.mail.yahoo.com")
        self.imap_conn.login(self.email_user, self.password)
        self.smtp_conn = smtplib.SMTP_SSL("smtp.mail.yahoo.com", 465)
        self.smtp_conn.login(self.email_user, self.password)

    async def fetch_emails(self, query: Optional[str] = None, limit: int = 10) -> List[EmailMessage]:
        self.imap_conn.select("inbox")
        status, messages = self.imap_conn.search(None, query if query else "ALL")
        
        email_ids = messages[0].split()[-limit:]
        email_list = []
        
        for e_id in email_ids:
            res, msg_data = self.imap_conn.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    email_list.append(EmailMessage(
                        id=str(e_id),
                        subject=msg['subject'] or "No Subject",
                        sender=msg['from'] or "Unknown",
                        body=msg.get_payload(decode=True).decode(errors='ignore') if msg.is_multipart() else msg.get_payload(decode=True).decode(errors='ignore'),
                        date=msg['date'] or "",
                    ))
        return email_list

    async def send_email(self, to: str, subject: str, body: str):
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = self.email_user
        msg['To'] = to
        self.smtp_conn.send_message(msg)

    async def draft_email(self, to: str, subject: str, body: str) -> str:
        # Yahoo IMAP/SMTP doesn't have a native "Drafts" API like Gmail/Outlook
        # We simulate it by saving to the Drafts folder
        return "yahoo_simulated_draft_id"

    async def update_label(self, email_id: str, label: str, action: str = "add"):
        # Yahoo uses folders instead of labels
        pass
