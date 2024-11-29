import asyncio
import logging
import subprocess
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
from typing import Any, Sequence

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/mac_control.log',
    filemode='w'
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("mac-control")

def run_applescript(script: str) -> str:
    """Run AppleScript and return its output."""
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"AppleScript error: {e.stderr}")
        raise ValueError(f"AppleScript failed: {e.stderr}")

def run_shell(command: str) -> str:
    """Run shell command and return its output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Shell command error: {e.stderr}")
        raise ValueError(f"Shell command failed: {e.stderr}")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="applescript",
            description="Run AppleScript command",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "AppleScript command to execute"
                    }
                },
                "required": ["script"]
            }
        ),
        Tool(
            name="shell",
            description="Run shell command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    }
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="volume",
            description="Control system volume",
            inputSchema={
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume level (0-100)",
                        "minimum": 0,
                        "maximum": 100
                    }
                },
                "required": ["level"]
            }
        ),
        Tool(
            name="notification",
            description="Send system notification",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Notification title"
                    },
                    "message": {
                        "type": "string",
                        "description": "Notification message"
                    }
                },
                "required": ["title", "message"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    if name == "applescript":
        output = run_applescript(arguments["script"])
        return [TextContent(type="text", text=f"✅ Done!\nOutput: {output}")]
    
    elif name == "shell":
        output = run_shell(arguments["command"])
        return [TextContent(type="text", text=f"✅ Done!\nOutput: {output}")]
    
    elif name == "volume":
        script = f'set volume output volume {arguments["level"]}'
        run_applescript(script)
        return [TextContent(
            type="text",
            text=f"🔊 Volume set to {arguments['level']}%"
        )]
    
    elif name == "notification":
        script = f'''
        display notification "{arguments['message']}" with title "{arguments['title']}"
        '''
        run_applescript(script)
        return [TextContent(
            type="text",
            text=f"🔔 Notification sent: {arguments['title']}"
        )]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    from mcp.server.stdio import stdio_server
    
    logger.debug("Starting mac-control server...")
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.debug("Server streams initialized")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mac-control",
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