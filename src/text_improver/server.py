import asyncio
import logging
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, SamplingMessage, SamplingContent
from typing import Any, Sequence

logger = logging.getLogger(__name__)
server = Server("text-improver")

class TextImprover:
    def __init__(self):
        self.current_text = None
        self.improvements = []
    
    def set_text(self, text: str):
        self.current_text = text
        self.improvements = []
    
    def get_text(self) -> str:
        return self.current_text
    
    def add_improvement(self, suggestion: str):
        self.improvements.append(suggestion)
    
    def get_improvements(self) -> list[str]:
        return self.improvements

improver = TextImprover()

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="set_text",
            description="Set text for improvement",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to improve"
                    }
                },
                "required": ["text"]
            }
        ),
        Tool(
            name="improve_text",
            description="Get improvements for current text",
            inputSchema={
                "type": "object",
                "properties": {
                    "style": {
                        "type": "string",
                        "description": "Improvement style (formal/creative/concise)",
                        "enum": ["formal", "creative", "concise"]
                    }
                },
                "required": ["style"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    global improver
    
    if name == "set_text":
        text = arguments["text"]
        improver.set_text(text)
        return [TextContent(
            type="text",
            text=f"Text set for improvement ({len(text)} characters)"
        )]
    
    elif name == "improve_text":
        if not improver.get_text():
            return [TextContent(
                type="text",
                text="No text set for improvement"
            )]
        
        style = arguments["style"]
        context = server.request_context
        
        # Create sampling message using MCP types
        message = SamplingMessage(
            role="user",
            content=SamplingContent(
                type="text",
                text=f"""Here's the text to improve:
                
{improver.get_text()}

Please suggest improvements to make this text more {style}."""
            )
        )
        
        # Ask the client to run the model
        result = await context.session.send_request(
            "sampling/createMessage",
            {
                "messages": [message.model_dump()],
                "systemPrompt": f"""You are a helpful writing assistant specializing in {style} writing.
Focus on specific, actionable improvements. Format your response as a list of suggestions.""",
                "includeContext": "thisServer",
                "maxTokens": 1000
            }
        )
        
        # Store improvement
        improver.add_improvement(result.content.text)
        
        return [TextContent(
            type="text",
            text=f"Improvements ({style}):\n\n{result.content.text}"
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
                    server_name="text-improver",
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