"""AI orchestration service for email and calendar tasks."""

import os
import re
from datetime import datetime
from typing import Any, Annotated, Optional, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from app.integrations.calendar.base import CalendarProvider, CalendarEvent
from app.integrations.email.base import EmailProvider
from app.services.conversation_memory import MemoryService


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class AIService:
    def __init__(
        self,
        email_provider: EmailProvider,
        calendar_provider: Optional[CalendarProvider] = None,
        session_id: str = "default",
        llm: Any | None = None,
    ):
        self.email_provider = email_provider
        self.calendar_provider = calendar_provider
        self.memory = MemoryService()
        self.session_id = session_id
        self.llm = llm or ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "gemma3:4b"),
            temperature=0,
        )
        self.graph = self._setup_graph()

    def _setup_graph(self):
        @tool("fetch_emails")
        async def fetch_emails(query: Optional[str] = None) -> list[dict[str, Any]]:
            """Fetch inbox emails, optionally filtered by a search query."""
            return await self.tool_fetch_emails_impl(query=query)

        @tool("draft_reply")
        async def draft_reply(email_id: str, body: str) -> str:
            """Create a draft reply to an email. Use this instead of sending email."""
            return await self.tool_draft_reply_impl(email_id, body)

        @tool("update_label")
        async def update_label(email_id: str, label: str) -> str:
            """Add a label or category to an email."""
            return await self.tool_update_label_impl(email_id, label)

        @tool("create_calendar_event")
        async def create_calendar_event(
            summary: str,
            start_time: str,
            end_time: str,
            description: Optional[str] = None,
        ) -> str:
            """Create a calendar event. Times must use ISO 8601 format."""
            return await self.tool_create_calendar_event_impl(
                summary, start_time, end_time, description
            )

        @tool("list_calendar_events")
        async def list_calendar_events(start_time: str, end_time: str) -> str:
            """List calendar events within an ISO 8601 time range."""
            return await self.tool_list_calendar_events_impl(start_time, end_time)

        tools = [
            fetch_emails,
            draft_reply,
            update_label,
            create_calendar_event,
            list_calendar_events,
        ]
        self.llm_with_tools = self.llm.bind_tools(tools)
        tool_node = ToolNode(tools)

        async def call_model(state: AgentState):
            messages = list(state["messages"])
            prompt = SystemMessage(
                content=(
                    "You are a concise AI email assistant. Use tools for inbox and "
                    "calendar information; never invent results. Email sending is disabled: "
                    "create a draft reply for the user to review instead. After a tool "
                    "result, answer directly and briefly."
                )
            )
            try:
                response = await self.llm_with_tools.ainvoke([prompt, *messages])
            except Exception as exc:
                return {"messages": [await self._fallback_response(messages, exc)]}
            return {"messages": [response]}

        def should_continue(state: AgentState):
            last_message = state["messages"][-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                return "tools"
            return END

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", call_model)
        workflow.add_node("tools", tool_node)
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", should_continue)
        workflow.add_edge("tools", "agent")
        return workflow.compile()

    async def _fallback_response(
        self, messages: Sequence[BaseMessage], error: Exception
    ) -> AIMessage:
        """Serve essential, safe requests when the local model is offline."""
        user_input = next(
            (
                message.content
                for message in reversed(messages)
                if isinstance(message, HumanMessage) and isinstance(message.content, str)
            ),
            "",
        )
        lower_input = user_input.lower()

        if "draft" in lower_input and "reply" in lower_input:
            match = re.search(
                r"(?:email|message)\s+([\w-]+).*?(?:saying|that says?)\s+(.+)",
                user_input,
                flags=re.IGNORECASE,
            )
            if match:
                result = await self.tool_draft_reply_impl(match.group(1), match.group(2))
                return AIMessage(content=result)

        if any(word in lower_input for word in ("email", "inbox", "fetch", "read")):
            emails = await self.tool_fetch_emails_impl()
            if not emails:
                return AIMessage(content="No emails found.")
            formatted = "\n".join(
                f"- {email['subject']} from {email['sender']}" for email in emails
            )
            return AIMessage(content=f"Inbox emails:\n{formatted}")

        return AIMessage(
            content=(
                "The local AI model is unavailable. Start Ollama with the configured "
                f"model and try again. ({type(error).__name__})"
            )
        )

    async def tool_fetch_emails_impl(
        self, query: Optional[str] = None
    ) -> list[dict[str, Any]]:
        emails = await self.email_provider.fetch_emails(query=query)
        return [email.model_dump() for email in emails]

    async def tool_draft_reply_impl(self, email_id: str, body: str) -> str:
        emails = await self.email_provider.fetch_emails(query=None, limit=100)
        original = next((email for email in emails if email.id == email_id), None)
        if not original:
            return "Could not find the original email to reply to."
        draft_id = await self.email_provider.draft_email(
            original.sender, f"Re: {original.subject}", body
        )
        return f"Draft created successfully with ID: {draft_id}"

    async def tool_update_label_impl(self, email_id: str, label: str) -> str:
        await self.email_provider.update_label(email_id, label)
        return f"Email {email_id} labeled as {label}"

    async def tool_create_calendar_event_impl(
        self, summary: str, start_time: str, end_time: str, description: Optional[str] = None
    ) -> str:
        if not self.calendar_provider:
            return "Calendar provider not configured."
        try:
            event = CalendarEvent(
                summary=summary,
                description=description,
                start_time=datetime.fromisoformat(start_time),
                end_time=datetime.fromisoformat(end_time),
            )
            event_id = await self.calendar_provider.create_event(event)
            return f"Appointment scheduled successfully with ID: {event_id}"
        except ValueError:
            return "Times must be valid ISO 8601 datetimes."
        except Exception as exc:
            return f"Failed to schedule appointment: {exc}"

    async def tool_list_calendar_events_impl(self, start_time: str, end_time: str) -> str:
        if not self.calendar_provider:
            return "Calendar provider not configured."
        try:
            events = await self.calendar_provider.list_events(
                datetime.fromisoformat(start_time), datetime.fromisoformat(end_time)
            )
        except ValueError:
            return "Times must be valid ISO 8601 datetimes."
        except Exception as exc:
            return f"Failed to list events: {exc}"
        if not events:
            return "No events found for this period."
        return "Upcoming events:\n" + "\n".join(
            f"- {event.summary} ({event.start_time} to {event.end_time})" for event in events
        )

    async def process_request(
        self, user_input: str, chat_history: Optional[list[dict[str, str]]] = None
    ) -> str:
        stored_history = self.memory.get_history(self.session_id)
        combined_history = stored_history + (chat_history or [])
        messages: list[BaseMessage] = []
        for message in combined_history:
            role = message.get("role")
            content = message.get("content")
            if not isinstance(content, str):
                continue
            messages.append(
                HumanMessage(content=content)
                if role in {"human", "user"}
                else AIMessage(content=content)
            )
        messages.append(HumanMessage(content=user_input))
        final_state = await self.graph.ainvoke({"messages": messages})
        content = final_state["messages"][-1].content
        final_response = content if isinstance(content, str) else str(content)
        self.memory.save_message(self.session_id, "human", user_input)
        self.memory.save_message(self.session_id, "ai", final_response)
        return final_response

    async def summarize_thread(self, email_id: str) -> str:
        emails = await self.email_provider.fetch_emails(query=None, limit=100)
        thread = [email for email in emails if email.id == email_id]
        if not thread:
            return "Could not find that email thread."
        context = "\n\n".join(
            f"From: {email.sender}\nSubject: {email.subject}\nBody: {email.body}"
            for email in thread
        )
        response = await self.llm.ainvoke(
            f"Summarize this email thread concisely:\n\n{context}"
        )
        return response.content
