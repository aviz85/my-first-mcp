import asyncio
import logging
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Resource, TextContent
from pydantic import AnyUrl
import subprocess
import base64
import os
from datetime import datetime

logger = logging.getLogger(__name__)
server = Server("screen-server")

class ScreenManager:
    def __init__(self):
        self.screenshots_dir = "/tmp/screenshots"
        os.makedirs(self.screenshots_dir, exist_ok=True)
    
    def take_screenshot(self, area: str = "full") -> str:
        """Take a screenshot and return its path"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{area}_{timestamp}.png"
        path = os.path.join(self.screenshots_dir, filename)
        
        if area == "full":
            cmd = f"screencapture -x '{path}'"
        elif area == "selection":
            cmd = f"screencapture -i '{path}'"
        else:  # window
            cmd = f"screencapture -w '{path}'"
        
        subprocess.run(cmd, shell=True, check=True)
        return path
    
    def get_screenshot_base64(self, path: str) -> str:
        """Get base64 encoded screenshot"""
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()

screen_mgr = ScreenManager()

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available screenshot resources"""
    return [
        Resource(
            uri=AnyUrl("screen://full"),
            name="Full Screen",
            mimeType="image/png",
            description="Take a screenshot of the entire screen"
        ),
        Resource(
            uri=AnyUrl("screen://selection"),
            name="Screen Selection",
            mimeType="image/png",
            description="Take a screenshot of a selected area"
        ),
        Resource(
            uri=AnyUrl("screen://window"),
            name="Active Window",
            mimeType="image/png",
            description="Take a screenshot of the active window"
        )
    ]

@server.read_resource()
async def read_resource(uri: AnyUrl) -> str:
    """Take and return a screenshot"""
    logger.debug(f"Reading resource: {uri}")
    
    try:
        # Extract area from URI
        area = str(uri).replace("screen://", "")
        if area not in ["full", "selection", "window"]:
            raise ValueError(f"Invalid screenshot area: {area}")
        
        # Take screenshot
        path = screen_mgr.take_screenshot(area)
        
        # Get base64 data
        image_data = screen_mgr.get_screenshot_base64(path)
        
        # Clean up
        os.remove(path)
        
        return f"data:image/png;base64,{image_data}"
        
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        raise

async def main():
    from mcp.server.stdio import stdio_server
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="screen-server",
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