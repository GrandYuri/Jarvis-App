import sys
import os
import json
from datetime import datetime

from openai import OpenAI

MODEL = "gpt-6-luna"

INSTRUCTIONS = """
You are J.A.R.V.I.S., a helpful personal AI assistant.
Answer in English.
Be clear, intelligent, practical, and honest.

You can use the available functions to perform actions on the user's
computer. Use a function when the user clearly requests a supported action.
Never claim an action was completed unless the function result confirms it.

CALENDAR RULES:
Adding an event requires all four fields:
1. Name/title
2. Date
3. Color
4. Priority (integer from 1 to 10)

If any field is missing or ambiguous, ask the user before calling
add_calendar_event. Never invent missing values or silently select defaults.
Ask for multiple missing fields in one message when appropriate.

Dates must use YYYY-MM-DD when calling the calendar function.
Ask for clarification if the date is ambiguous.

COLOR RULES:
Available standard colors:
Red, Green, Blue, Forest, Yellow, Turquoise, Cyan, Pink, Orange,
Purple, Brown, Black, White.

Custom 1, Custom 2, and Custom 3 are available when explicitly requested.

When the user describes a color, first choose the closest suitable
color from the available list.
If none is a suitable match, choose an appropriate HEX color.
If the user provides a HEX code, preserve it.
If no color is specified or implied, ask the user.

PRIORITY:
Priority must be an integer from 1 to 10.
If missing, ask the user. Never invent it.

Use web search for current information, recent events, changing facts,
and questions that need online research.
When using web search, provide useful source links.
Never invent sources or claim to have searched when you have not.

Remember conversation history and supplied saved-chat context.
If asked for the current chat name, use the exact name from
the CURRENT CHAT NAME context.
Do not confuse the current chat with other saved chats.

CALENDAR EVENT IDENTIFICATION:
- Calendar events have five identifying properties:
  ID, title, date, priority, and color.
- Use get_calendar_events to inspect existing events when needed.
- Consider all five properties when identifying the intended event.
- Treat ID as the unique identifier of an event.
- Prefer an exact ID match whenever an ID is available.
- When the user identifies an event by its title, date, priority,
  or color, compare that information with the actual calendar data.
- Never invent an event, ID, date, priority, or color.
- If multiple events match the user's description, ask the user
  to clarify which event they mean.
- Before requesting deletion, verify the event's title and date.
- When describing a pending deletion, include its title, date,
  priority, color, and ID whenever available.

CALENDAR EVENT SELECTION AND EDITING:
- Always inspect get_calendar_events before selecting an event to edit or delete.
- Consider all events on the requested date, not just the first match.
- Compare the title, date, priority, and color with the user's description.
- Every event has a unique ID. Use the selected event's exact ID for edit/delete.
- Never select an event based only on its title if other matching events exist.
- If the user's description matches multiple events, ask which one they mean.
- Never invent, modify, or guess an event ID.
- Editing must update the existing event; never replace it by creating a duplicate.
- Preserve all unchanged properties during an edit.
- Deletion must be confirmed by the user in chat before the event is removed.

DELETION CONFIRMATION:
- Never ask for confirmation before calling delete_calendar_event.
- Call the tool once to stage the requested deletion.
- The tool does not delete events; it only stages the operation.
- After the tool returns, show every selected event and ask for
  exactly one explicit yes/no confirmation.
- The application handles the user's confirmation directly.
- Never ask the user to confirm again in the interface.
- Never call delete_calendar_event again just because the user
  confirmed an already staged deletion.
- Never claim that deletion is complete until the application
  confirms that it succeeded.

MULTIPLE EVENT DELETION:
- When the user asks to delete multiple events, inspect all calendar events.
- Select every event that matches the user's requested criteria.
- Pass all selected event IDs in one delete_calendar_event call.
- Never split a multi-event deletion into separate tool calls.
- Before confirmation, list every selected event with its ID, title,
  date, priority, and color.
- Ask for one explicit confirmation for the complete list.
- If the requested group is ambiguous, ask for clarification.
- Never include events that do not match the user's request.
"""

TOOLS = [
    {"type": "web_search"},
    {
        "type": "function",
        "name": "get_current_time",
        "description": "Get the current local time.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_current_date",
        "description": "Get the current local date.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "open_website",
        "description": "Open YouTube or Google in the browser.",
        "parameters": {
            "type": "object",
            "properties": {
                "site": {
                    "type": "string",
                    "enum": ["youtube", "google"],
                },
            },
            "required": ["site"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "launch_notepad",
        "description": "Launch Windows Notepad.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "set_window_mode",
        "description": "Set J.A.R.V.I.S. to fullscreen or windowed mode.",
        "parameters": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["fullscreen", "windowed"],
                },
            },
            "required": ["mode"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "add_calendar_event",
        "description": (
            "Add an event to the J.A.R.V.I.S. calendar. "
            "Only call this after the user has provided all four fields: "
            "title, date, color, and priority. "
            "Date must be YYYY-MM-DD. "
            "Color must be a listed color, Custom 1-3, or a valid HEX code. "
            "Priority must be an integer from 1 to 10."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The event name.",
                },
                "date": {
                    "type": "string",
                    "description": "Event date in YYYY-MM-DD format.",
                },
                "color": {
                    "type": "string",
                    "description": "A listed color, Custom 1-3, or HEX.",
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority from 1 to 10.",
                },
            },
            "required": ["title", "date", "color", "priority"],
            "additionalProperties": False,
        },
        "strict": True,
    },
        {
        "type": "function",
        "name": "get_calendar_events",
        "description": (
            "List calendar events with their IDs, titles, dates, "
            "colors, and priorities. Use this before editing or "
            "deleting an existing event if its exact identity is unclear."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
            "additionalProperties": False,
        },
        "strict": True,
    },

    {
        "type": "function",
        "name": "delete_calendar_event",
        "description": (
            "Request deletion of one or more exact calendar events by ID. "
            "First inspect get_calendar_events. Compare title, date, "
            "priority, and color. Consider all events matching the request. "
            "Pass every selected unique ID in event_ids in a single call. "
            "The application will ask for confirmation before deletion."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "event_ids": {
                    "type": "array",
                    "items": {
                        "type": "string",
                    },
                    "description": (
                        "IDs of all exact events the user requested to delete."
                    ),
                },
            },
            "required": ["event_ids"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "edit_calendar_event",
        "description": (
            "Edit one existing calendar event selected by its unique ID. "
            "First inspect get_calendar_events and compare the title, date, "
            "priority, and color. Consider other events on the same date. "
            "Pass the chosen event's ID and all five final event properties. "
            "For unchanged properties, preserve their existing values. "
            "Do not create a new event when editing."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "Unique ID of the event to edit.",
                },
                "title": {
                    "type": "string",
                    "description": "Final event title.",
                },
                "date": {
                    "type": "string",
                    "description": "Final date in YYYY-MM-DD format.",
                },
                "priority": {
                    "type": "integer",
                    "description": "Final priority from 1 to 10.",
                },
                "color": {
                    "type": "string",
                    "description": "Final color name or HEX color.",
                },
            },
            "required": [
                "event_id",
                "title",
                "date",
                "priority",
                "color",
            ],
            "additionalProperties": False,
        },
        "strict": True,
    }
]


def ask_jarvis(
    message: str,
    history: list | None = None,
    other_chats: str | None = None,
    tool_executor=None,
) -> str:
    if not os.getenv("OPENAI_API_KEY"):
        return (
            "Missing API key. Set OPENAI_API_KEY "
            "in your environment variables."
        )

    try:
        client = OpenAI()
        conversation = []

        conversation.append({
            "role": "developer",
            "content": (
                f"Current local date: {datetime.now().date().isoformat()}.\n"
                f"Current local time: {datetime.now().strftime('%H:%M:%S')}."
            ),
        })

        if other_chats:
            conversation.append({
                "role": "developer",
                "content": (
                    "Context about the current and saved chats:\n"
                    + other_chats
                ),
            })

        if history:
            for item in history[-10:]:
                role = item.get("role")
                content = item.get("content", "")

                if role in ("user", "assistant") and content:
                    conversation.append({
                        "role": role,
                        "content": content,
                    })

        conversation.append({
            "role": "user",
            "content": message,
        })

        # Allow the model to call functions and then use their results.
        for _ in range(6):
            response = client.responses.create(
                model=MODEL,
                instructions=INSTRUCTIONS,
                tools=TOOLS,
                input=conversation,
                max_output_tokens=1000,
            )

            usage = response.usage

            if usage:
                details = getattr(
                    usage,
                    "input_tokens_details",
                    None
                )

                cached = getattr(
                    details,
                    "cached_tokens",
                    0
                )

                print(
                    f"[JARVIS TOKENS] "
                    f"Input: {usage.input_tokens} | "
                    f"Cached input: {cached} | "
                    f"Output: {usage.output_tokens}"
                )

            function_calls = [
                item
                for item in response.output
                if getattr(item, "type", None) == "function_call"
            ]

            if not function_calls:
                answer = response.output_text.strip()

                if answer:
                    return answer

                return "I couldn't generate a text response."

            # Keep the model's tool-call items in the conversation.
            conversation.extend(response.output)

            for call in function_calls:
                try:
                    arguments = json.loads(call.arguments)

                    if tool_executor is None:
                        result = {
                            "ok": False,
                            "message": "Function execution is unavailable.",
                        }
                    else:
                        result = tool_executor(call.name, arguments)

                    if not isinstance(result, dict):
                        result = {
                            "ok": False,
                            "message": "The function returned an invalid result.",
                        }

                except Exception as error:
                    result = {
                        "ok": False,
                        "message": str(error),
                    }

                conversation.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": json.dumps(
                        result,
                        ensure_ascii=False,
                    ),
                })

        return "I couldn't finish the requested action. Please try again."

    except Exception as error:
        return f"AI connection error: {error}"