import asyncio
import logging
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
from typing import Any, Sequence
import base64
from PIL import Image
import io
import os
import json

logger = logging.getLogger(__name__)
server = Server("image-analyzer")

class ImageAnalyzer:
    def __init__(self):
        self.current_image = None
        self.current_image_path = None
    
    def load_image(self, path: str) -> bool:
        try:
            self.current_image = Image.open(path)
            self.current_image_path = path
            return True
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return False
    
    def get_image_info(self) -> dict:
        if not self.current_image:
            return None
        
        return {
            'format': self.current_image.format,
            'size': self.current_image.size,
            'mode': self.current_image.mode,
            'path': self.current_image_path
        }
    
    def get_image_base64(self) -> str:
        if not self.current_image:
            return None
        
        buffered = io.BytesIO()
        self.current_image.save(buffered, format=self.current_image.format)
        return base64.b64encode(buffered.getvalue()).decode()

analyzer = ImageAnalyzer()

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_image",
            description="Load and analyze an image file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to image file"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="get_analysis",
            description="Get current image analysis",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    global analyzer
    
    if name == "analyze_image":
        path = arguments["path"]
        if analyzer.load_image(path):
            info = analyzer.get_image_info()
            return [TextContent(
                type="text",
                text=f"Successfully loaded image:\n{json.dumps(info, indent=2)}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Failed to load image: {path}"
            )]
    
    elif name == "get_analysis":
        info = analyzer.get_image_info()
        if info:
            context = server.request_context
            
            # Create messages array
            messages = [
                {
                    "role": "user",
                    "content": {
                        "type": "image",
                        "data": analyzer.get_image_base64(),
                        "mimeType": f"image/{info['format'].lower()}"
                    }
                },
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": "Please analyze this image and describe what you see."
                    }
                }
            ]
            
            # Send request with separate parameters
            result = await context.session.create_message(
                messages=messages,
                max_tokens=500,
                system_prompt="You are a helpful image analysis assistant.",
                model_preferences={
                    "hints": [{"name": "claude-3"}],
                    "intelligencePriority": 1.0
                }
            )
            
            return [TextContent(
                type="text",
                text=f"Image Analysis:\n\n{result.content.text}"
            )]
        else:
            return [TextContent(
                type="text",
                text="No image loaded"
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
                    server_name="image-analyzer",
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