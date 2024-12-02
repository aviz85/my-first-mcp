import asyncio
import logging
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
from typing import Any, Sequence
import os.path
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)
server = Server("gmail-assistant")

# Gmail API setup
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_service():
    """Get authenticated Gmail service"""
    creds = None
    creds_path = os.path.join(os.path.dirname(__file__), '..', '..', 'credentials.json')
    token_path = os.path.join(os.path.dirname(creds_path), 'token.json')
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return build('gmail', 'v1', credentials=creds)

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="list_messages",
            description="List recent email messages",
            inputSchema={
                "type": "object",
                "properties": {
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of messages to return",
                        "default": 10
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query (Gmail search syntax)",
                        "default": ""
                    }
                }
            }
        ),
        Tool(
            name="send_email",
            description="Send a new email",
            inputSchema={
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address"
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject"
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body (plain text)"
                    }
                },
                "required": ["to", "subject", "body"]
            }
        ),
        Tool(
            name="get_message",
            description="Get a specific email message",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Message ID"
                    }
                },
                "required": ["message_id"]
            }
        ),
        Tool(
            name="search_emails",
            description="Search for emails",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 10
                    }
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    service = get_gmail_service()
    
    if name == "list_messages":
        max_results = arguments.get("max_results", 10)
        query = arguments.get("query", "")
        
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()
        
        messages = []
        for msg in results.get('messages', []):
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            messages.append(
                f"• From: {headers.get('From', 'Unknown')}\n"
                f"  Subject: {headers.get('Subject', '(no subject)')}\n"
                f"  Date: {headers.get('Date', 'Unknown')}\n"
                f"  ID: {message['id']}"
            )
        
        return [TextContent(
            type="text",
            text="Recent messages:\n\n" + "\n\n".join(messages)
        )]
    
    elif name == "send_email":
        from email.mime.text import MIMEText
        import base64
        
        message = MIMEText(arguments["body"])
        message['to'] = arguments["to"]
        message['subject'] = arguments["subject"]
        
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        try:
            service.users().messages().send(
                userId='me',
                body={'raw': raw}
            ).execute()
            
            return [TextContent(
                type="text",
                text=f"✅ Email sent to {arguments['to']}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Failed to send email: {str(e)}"
            )]
    
    elif name == "get_message":
        message = service.users().messages().get(
            userId='me',
            id=arguments["message_id"]
        ).execute()
        
        headers = {h['name']: h['value'] for h in message['payload']['headers']}
        
        # Get message body
        body = ""
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(
                        part['body']['data']
                    ).decode()
                    break
        elif 'body' in message['payload']:
            body = base64.urlsafe_b64decode(
                message['payload']['body']['data']
            ).decode()
        
        return [TextContent(
            type="text",
            text=f"""Email details:
From: {headers.get('From', 'Unknown')}
To: {headers.get('To', 'Unknown')}
Subject: {headers.get('Subject', '(no subject)')}
Date: {headers.get('Date', 'Unknown')}

{body}"""
        )]
    
    elif name == "search_emails":
        results = service.users().messages().list(
            userId='me',
            maxResults=arguments.get("max_results", 10),
            q=arguments["query"]
        ).execute()
        
        messages = []
        for msg in results.get('messages', []):
            message = service.users().messages().get(
                userId='me',
                id=msg['id'],
                format='metadata',
                metadataHeaders=['From', 'Subject', 'Date']
            ).execute()
            
            headers = {h['name']: h['value'] for h in message['payload']['headers']}
            messages.append(
                f"• From: {headers.get('From', 'Unknown')}\n"
                f"  Subject: {headers.get('Subject', '(no subject)')}\n"
                f"  Date: {headers.get('Date', 'Unknown')}\n"
                f"  ID: {message['id']}"
            )
        
        return [TextContent(
            type="text",
            text=f"Search results for '{arguments['query']}':\n\n" + 
                 "\n\n".join(messages)
        )]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    from mcp.server.stdio import stdio_server
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="gmail-assistant",
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
    asyncio.run(main()) 