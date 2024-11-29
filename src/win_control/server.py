import asyncio
import logging
import subprocess
import ctypes
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
from typing import Any, Sequence
import winreg
from pathlib import Path
import os

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=str(Path.home() / 'AppData' / 'Local' / 'win_control.log'),
    filemode='w'
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("win-control")

def run_powershell(script: str) -> str:
    """Run PowerShell command and return its output."""
    try:
        result = subprocess.run(
            ['powershell', '-Command', script],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"PowerShell error: {e.stderr}")
        raise ValueError(f"PowerShell failed: {e.stderr}")

def run_cmd(command: str) -> str:
    """Run CMD command and return its output."""
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
        logger.error(f"CMD error: {e.stderr}")
        raise ValueError(f"CMD failed: {e.stderr}")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="powershell",
            description="Run PowerShell command",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "PowerShell command to execute"
                    }
                },
                "required": ["script"]
            }
        ),
        Tool(
            name="cmd",
            description="Run CMD command",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "CMD command to execute"
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
        ),
        Tool(
            name="lock",
            description="Lock Windows",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="screenshot",
            description="Take a screenshot",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Save path (optional)",
                        "default": str(Path.home() / "Pictures" / "screenshot.png")
                    }
                }
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    if name == "powershell":
        output = run_powershell(arguments["script"])
        return [TextContent(type="text", text=f"✅ Done!\nOutput: {output}")]
    
    elif name == "cmd":
        output = run_cmd(arguments["command"])
        return [TextContent(type="text", text=f"✅ Done!\nOutput: {output}")]
    
    elif name == "volume":
        script = f'''
        $obj = New-Object -ComObject WScript.Shell
        $obj.SendKeys([char]174 * 50)  # Mute first
        $obj.SendKeys([char]175 * {int(arguments["level"] / 2)})  # Then set volume
        '''
        run_powershell(script)
        return [TextContent(
            type="text",
            text=f"🔊 Volume set to {arguments['level']}%"
        )]
    
    elif name == "notification":
        script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null

        $template = @"
        <toast>
            <visual>
                <binding template="ToastText02">
                    <text id="1">{arguments['title']}</text>
                    <text id="2">{arguments['message']}</text>
                </binding>
            </visual>
        </toast>
"@

        $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
        $xml.LoadXml($template)
        $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Windows Control").Show($toast)
        '''
        run_powershell(script)
        return [TextContent(
            type="text",
            text=f"🔔 Notification sent: {arguments['title']}"
        )]
    
    elif name == "lock":
        ctypes.windll.user32.LockWorkStation()
        return [TextContent(
            type="text",
            text="🔒 Windows locked"
        )]
    
    elif name == "screenshot":
        save_path = arguments.get("path", str(Path.home() / "Pictures" / "screenshot.png"))
        script = f'''
        Add-Type -AssemblyName System.Windows.Forms
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $bitmap.Save('{save_path}')
        $graphics.Dispose()
        $bitmap.Dispose()
        '''
        run_powershell(script)
        return [TextContent(
            type="text",
            text=f"📸 Screenshot saved to: {save_path}"
        )]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    from mcp.server.stdio import stdio_server
    
    logger.debug("Starting win-control server...")
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.debug("Server streams initialized")
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="win-control",
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