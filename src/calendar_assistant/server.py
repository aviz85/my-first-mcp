import datetime
from datetime import timedelta
import pytz
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import (
    Resource, Tool, TextContent, PromptMessage, Prompt, PromptArgument, GetPromptResult
)
from pydantic import AnyUrl
from typing import Any, Sequence
import logging
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os.path
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/calendar_assistant.log',
    filemode='w'
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("calendar-assistant")

# Google Calendar setup
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/calendar.events']

def verify_credentials():
    creds_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
    abs_path = os.path.abspath(creds_path)
    logger.debug(f"Looking for credentials at: {abs_path}")
    
    if not os.path.exists(abs_path):
        logger.error(f"credentials.json not found at {abs_path}")
        raise FileNotFoundError(
            "credentials.json not found. Please download it from Google Cloud Console "
            "and place it in the project root directory."
        )
    
    try:
        with open(abs_path) as f:
            creds_data = json.load(f)
            if 'installed' not in creds_data:
                logger.error("Invalid credentials.json format - missing 'installed' key")
                raise ValueError("Invalid credentials.json format")
            logger.debug("Found valid credentials.json")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in credentials.json: {str(e)}")
        raise ValueError("credentials.json is not valid JSON")
    
    return abs_path

def get_calendar_service():
    logger.debug("Starting calendar service initialization")
    creds = None
    creds_path = verify_credentials()
    token_path = os.path.join(os.path.dirname(creds_path), 'token.json')
    logger.debug(f"Token path: {token_path}")
    
    if os.path.exists(token_path):
        logger.debug("Found existing token.json")
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        logger.debug("Credentials invalid or expired, starting OAuth flow")
        if creds and creds.expired and creds.refresh_token:
            logger.debug("Attempting to refresh expired token")
            creds.refresh(Request())
        else:
            logger.debug("Starting new OAuth flow")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_path, SCOPES)
                logger.debug("Created OAuth flow")
                auth_url = flow.authorization_url()[0]
                print(f"\nPlease visit this URL to authenticate:\n{auth_url}\n")  # Print to stdout
                logger.info(f"\nAuth URL: {auth_url}\n")  # Also log it
                creds = flow.run_local_server(
                    port=0,
                    open_browser=True,
                    success_message="Authentication successful! You can close this window."
                )
                logger.debug("OAuth flow completed")
            except Exception as e:
                logger.error(f"OAuth flow error: {str(e)}", exc_info=True)
                raise
        
        logger.debug(f"Saving new token to {token_path}")
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    logger.debug("Building calendar service")
    return build('calendar', 'v3', credentials=creds)

# Resource handlers
@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available calendar resources."""
    return [
        Resource(
            uri=AnyUrl("calendar://events/today"),
            name="Today's Events",
            mimeType="application/json",
            description="Get today's calendar events"
        )
    ]

@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Read calendar data."""
    logger.debug(f"Reading resource: {uri}")
    try:
        service = get_calendar_service()
        logger.debug("Calendar service initialized")
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        
        if str(uri) == "calendar://events/today":
            logger.debug("Fetching today's events")
            end = (datetime.datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z'
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=end,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            logger.debug(f"Found {len(events)} events")
            
            return json.dumps([{
                'summary': event.get('summary', 'No title'),
                'start': event['start'].get('dateTime', event['start'].get('date')),
                'end': event['end'].get('dateTime', event['end'].get('date'))
            } for event in events], indent=2)
    except Exception as e:
        logger.error(f"Error reading calendar: {str(e)}", exc_info=True)
        raise

# Tool handlers
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="quick_add",
            description="Quickly add an event",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Event description (e.g., 'Meeting with John tomorrow at 3pm')"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="next",
            description="Show next meeting",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="cancel_next",
            description="Cancel your next meeting",
            inputSchema={
                "type": "object",
                "properties": {
                    "notify": {
                        "type": "boolean",
                        "description": "Notify attendees",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="free_today",
            description="Find free time slots today",
            inputSchema={
                "type": "object",
                "properties": {
                    "min_duration": {
                        "type": "integer",
                        "description": "Minimum duration in minutes",
                        "default": 30
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    service = get_calendar_service()
    
    if name == "quick_add":
        event = service.events().quickAdd(
            calendarId='primary',
            text=arguments["text"]
        ).execute()
        
        return [TextContent(
            type="text",
            text=f"✅ Added: {event['summary']}"
        )]
    
    elif name == "next":
        now = datetime.datetime.utcnow()
        events = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            maxResults=1,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])
        
        if not events:
            return [TextContent(type="text", text="No upcoming meetings! 🎉")]
        
        event = events[0]
        start = datetime.datetime.fromisoformat(
            event['start'].get('dateTime', event['start'].get('date')).replace('Z', '+00:00')
        )
        
        return [TextContent(
            type="text",
            text=f"Next up: {event['summary']} at {start.strftime('%H:%M')}"
        )]
    
    elif name == "cancel_next":
        now = datetime.datetime.utcnow()
        events = service.events().list(
            calendarId='primary',
            timeMin=now.isoformat() + 'Z',
            maxResults=1,
            singleEvents=True,
            orderBy='startTime'
        ).execute().get('items', [])
        
        if not events:
            return [TextContent(type="text", text="No meetings to cancel! 🎉")]
        
        event = events[0]
        service.events().delete(
            calendarId='primary',
            eventId=event['id'],
            sendUpdates='all' if arguments.get('notify', True) else 'none'
        ).execute()
        
        return [TextContent(
            type="text",
            text=f"Cancelled: {event['summary']}"
        )]
    
    elif name == "free_today":
        now = datetime.datetime.now(pytz.UTC)
        end_of_day = now.replace(hour=23, minute=59, second=59)
        min_duration = timedelta(minutes=arguments.get('min_duration', 30))
        
        # Get busy periods
        body = {
            "timeMin": now.isoformat(),
            "timeMax": end_of_day.isoformat(),
            "items": [{"id": "primary"}]
        }
        
        free_busy = service.freebusy().query(body=body).execute()
        busy = free_busy['calendars']['primary']['busy']
        
        if not busy:
            return [TextContent(
                type="text",
                text=f"You're free for the rest of the day! 🎉"
            )]
        
        # Find gaps
        free_slots = []
        current = now
        
        for period in busy:
            busy_start = datetime.datetime.fromisoformat(period['start'].replace('Z', '+00:00'))
            if busy_start - current >= min_duration:
                free_slots.append(f"• {current.strftime('%H:%M')} - {busy_start.strftime('%H:%M')}")
            current = datetime.datetime.fromisoformat(period['end'].replace('Z', '+00:00'))
        
        if end_of_day - current >= min_duration:
            free_slots.append(f"• {current.strftime('%H:%M')} - {end_of_day.strftime('%H:%M')}")
        
        if not free_slots:
            return [TextContent(type="text", text="No free slots found for today 😅")]
        
        return [TextContent(
            type="text",
            text="Free slots today:\n" + "\n".join(free_slots)
        )]
    
    raise ValueError(f"Unknown tool: {name}")

# Prompt handlers
@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available calendar prompts."""
    return [
        Prompt(
            name="suggest_meeting_time",
            description="Get suggestions for meeting times",
            arguments=[
                PromptArgument(
                    name="duration",
                    description="Meeting duration in minutes",
                    required=True
                ),
                PromptArgument(
                    name="participants",
                    description="Number of participants",
                    required=True
                )
            ]
        )
    ]

@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None) -> GetPromptResult:
    """Get calendar prompts."""
    if name != "suggest_meeting_time":
        raise ValueError(f"Unknown prompt: {name}")

    if not arguments or "duration" not in arguments or "participants" not in arguments:
        raise ValueError("Duration and participants are required")

    return GetPromptResult(
        description="Meeting time suggestions",
        messages=[
            PromptMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=f"Suggest optimal meeting times for a {arguments['duration']} minute meeting with {arguments['participants']} participants"
                )
            )
        ]
    )

# Main entry point
async def main():
    from mcp.server.stdio import stdio_server
    
    logger.debug(f"Python executable: {sys.executable}")
    logger.debug(f"Python version: {sys.version}")
    logger.debug("Starting calendar assistant server...")
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.debug("Server streams initialized")
            logger.debug(f"Server capabilities: {server.get_capabilities(notification_options=NotificationOptions(), experimental_capabilities={})}")
            
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="calendar-assistant",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )
    except Exception as e:
        logger.error(f"Server error: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 