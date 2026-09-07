"""Optional background inbox monitor."""

import asyncio
import logging
from datetime import datetime
from app.services.email_agent import AIService
from app.integrations.email.base import EmailProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ProactiveWorker")

class ProactiveEmailWorker:
    def __init__(self, email_provider: EmailProvider, ai_service: AIService):
        self.email_provider = email_provider
        self.ai_service = ai_service
        self.is_running = False
        self.processed_email_ids: set[str] = set()

    async def monitor_inbox(self, interval_seconds: int = 300):
        """
        Periodically checks for new emails and processes them proactively.
        """
        self.is_running = True
        logger.info("Proactive Worker started. Monitoring inbox...")
        
        while self.is_running:
            try:
                logger.info(f"Checking for new emails at {datetime.now()}...")
                # Fetch emails from the last 15 minutes
                emails = await self.email_provider.fetch_emails(limit=10)
                
                if not emails:
                    logger.info("No new emails to process.")
                else:
                    for email in emails:
                        if email.id in self.processed_email_ids:
                            continue
                        await self._process_email_proactively(email)
                        self.processed_email_ids.add(email.id)
                
            except Exception as e:
                logger.error(f"Error in proactive monitor: {str(e)}")
            
            await asyncio.sleep(interval_seconds)

    async def _process_email_proactively(self, email):
        """
        Analyzes an email and decides if a proactive action (like drafting a reply) is needed.
        """
        logger.info(f"Analyzing email: {email.subject}")
        
        prompt = (
            f"You are in proactive mode. Analyze this email and decide if it requires a draft reply "
            f"or a calendar appointment. If yes, perform the action. If not, ignore it.\n\n"
            f"From: {email.sender}\nSubject: {email.subject}\nBody: {email.body}"
        )
        
        # We use the AI service to handle the reasoning and tool calling
        response = await self.ai_service.process_request(prompt)
        logger.info(f"Proactive Action Result: {response}")

    def stop(self):
        self.is_running = False
        logger.info("Proactive Worker stopped.")
