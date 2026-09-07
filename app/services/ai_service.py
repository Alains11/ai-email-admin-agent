import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools import tool
from app.integrations.email.base import EmailProvider, EmailMessage
from app.integrations.calendar.base import CalendarProvider, CalendarEvent
from app.services.memory_service import MemoryService
from datetime import datetime

class AIService:
    def __init__(self, email_provider: EmailProvider, calendar_provider: CalendarProvider = None, session_id: str = "default"):
        self.email_provider = email_provider
        self.calendar_provider = calendar_provider
        self.memory = MemoryService()
        self.session_id = session_id
        self.llm = ChatOpenAI(model="gpt-4o", temperature=0)
        self.agent_executor = self._setup_agent()

    def _setup_agent(self) -> AgentExecutor:
        # Define tools for the agent
        tools = [
            self.tool_fetch_emails,
            self.tool_send_email,
            self.tool_draft_reply,
            self.tool_update_label,
            self.tool_create_calendar_event,
            self.tool_list_calendar_events
        ]

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a professional AI Email Assistant. Your goal is to help the user manage their inbox efficiently. "
                       "You can fetch emails, draft replies, send emails, and categorize them. "
                       "Always be polite, concise, and context-aware. If you are drafting a reply, "
                       "ensure it matches the tone of the original email."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_openai_functions_agent(self.llm, tools, prompt)
        return AgentExecutor(agent=agent, tools=tools, verbose=True)

    @tool
    async def tool_fetch_emails(self, query: str = None) -> List[Dict[str, Any]]:
        """Fetches emails from the inbox. Optional query for filtering."""
        emails = await self.email_provider.fetch_emails(query=query)
        return [email.dict() for email in emails]

    @tool
    async def tool_send_email(self, to: str, subject: str, body: str) -> str:
        """Sends an email to a recipient."""
        await self.email_provider.send_email(to, subject, body)
        return f"Email successfully sent to {to}"

    @tool
    async def tool_draft_reply(self, email_id: str, body: str) -> str:
        """Creates a draft reply for a specific email ID."""
        # First fetch the original email to get context (to, subject)
        emails = await self.email_provider.fetch_emails(query=None, limit=100) # Simplified
        original = next((e for e in emails if e.id == email_id), None)
        
        if not original:
            return "Could not find the original email to reply to."
            
        subject = f"Re: {original.subject}"
        draft_id = await self.email_provider.draft_email(original.sender, subject, body)
        return f"Draft created successfully with ID: {draft_id}"

    @tool
    async def tool_update_label(self, email_id: str, label: str) -> str:
        """Categorizes an email by adding a label."""
        await self.email_provider.update_label(email_id, label)
        return f"Email {email_id} labeled as {label}"

    @tool
    async def tool_create_calendar_event(self, summary: str, start_time: str, end_time: str, description: str = None) -> str:
        """Schedules an appointment in the calendar. Times should be in ISO format."""
        if not self.calendar_provider:
            return "Calendar provider not configured."
        
        try:
            event = CalendarEvent(
                summary=summary,
                description=description,
                start_time=datetime.fromisoformat(start_time),
                end_time=datetime.fromisoformat(end_time)
            )
            event_id = await self.calendar_provider.create_event(event)
            return f"Appointment scheduled successfully with ID: {event_id}"
        except Exception as e:
            return f"Failed to schedule appointment: {str(e)}"

    @tool
    async def tool_list_calendar_events(self, start_time: str, end_time: str) -> str:
        """Lists appointments in the calendar for a given time range. Times in ISO format."""
        if not self.calendar_provider:
            return "Calendar provider not configured."
        
        try:
            events = await self.calendar_provider.list_events(
                start_time=datetime.fromisoformat(start_time),
                end_time=datetime.fromisoformat(end_time)
            )
            if not events:
                return "No events found for this period."
            
            event_list = "\n".join([f"- {e.summary} ({e.start_time} to {e.end_time})" for e in events])
            return f"Upcoming events:\n{event_list}"
        except Exception as e:
            return f"Failed to list events: {str(e)}"

    async def process_request(self, user_input: str, chat_history: List = []) -> str:
        """Main entry point for the AI to handle user requests."""
        # Load history from memory
        stored_history = self.memory.get_history(self.session_id)
        combined_history = stored_history + chat_history
        
        result = await self.agent_executor.ainvoke({
            "input": user_input,
            "chat_history": combined_history
        })
        
        # Save interaction to memory
        self.memory.save_message(self.session_id, "human", user_input)
        self.memory.save_message(self.session_id, "ai", result["output"])
        
        return result["output"]

    async def summarize_thread(self, email_id: str) -> str:
        """Specialized method for summarizing a specific email thread."""
        emails = await self.email_provider.fetch_emails(query=None) # Simplified
        thread = [e for e in emails if e.id == email_id] # Simplified
        
        context = "\n".join([f"From: {e.sender}\nSubject: {e.subject}\nBody: {e.body}" for e in thread])
        response = await self.llm.ainvoke(f"Please summarize the following email thread concisely:\n\n{context}")
        return response.content
