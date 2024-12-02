import asyncio
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
from typing import Any, Sequence

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/file_watcher.log',
    filemode='w'
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("file-watcher")

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, server: Server):
        self.server = server
        super().__init__()

    async def notify_change(self, event_type: str, path: str):
        message = f"{event_type}: {path}"
        await self.server.notify_status(message)
        logger.debug(message)

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory:
            asyncio.create_task(
                self.notify_change(" File created", event.src_path)
            )

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory:
            asyncio.create_task(
                self.notify_change("✏️ File modified", event.src_path)
            )

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory:
            asyncio.create_task(
                self.notify_change("🗑️ File deleted", event.src_path)
            )

    def on_moved(self, event: FileSystemEvent):
        if not event.is_directory:
            asyncio.create_task(
                self.notify_change("📦 File moved/renamed", 
                                 f"{event.src_path} -> {event.dest_path}")
            )

class DirectoryWatcher:
    def __init__(self, server: Server):
        self.server = server
        self.observer = None
        self.watching = set()

    def start_watching(self, path: str):
        if path in self.watching:
            return False
        
        if self.observer is None:
            self.observer = Observer()
            self.observer.start()
        
        abs_path = str(Path(path).expanduser().resolve())
        event_handler = FileChangeHandler(self.server)
        self.observer.schedule(event_handler, abs_path, recursive=False)
        
        self.watching.add(path)
        return True

    def stop_watching(self, path: str):
        if path not in self.watching:
            return False
        
        abs_path = str(Path(path).expanduser().resolve())
        if self.observer:
            for watch in self.observer.watches.copy():
                if watch.path == abs_path:
                    self.observer.unschedule(watch)
        
        self.watching.remove(path)
        return True

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        self.watching.clear()

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="watch",
            description="Start watching a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to watch"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="unwatch",
            description="Stop watching a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to stop watching"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="list_watched",
            description="List currently watched directories",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

# Global watcher instance
watcher = None

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    global watcher
    
    if name == "watch":
        path = arguments["path"]
        if watcher.start_watching(path):
            return [TextContent(
                type="text",
                text=f"✅ Started watching: {path}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Already watching: {path}"
            )]
    
    elif name == "unwatch":
        path = arguments["path"]
        if watcher.stop_watching(path):
            return [TextContent(
                type="text",
                text=f"✅ Stopped watching: {path}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Not watching: {path}"
            )]
    
    elif name == "list_watched":
        if not watcher.watching:
            return [TextContent(
                type="text",
                text="No directories being watched"
            )]
        
        paths = "\n".join(f"• {path}" for path in watcher.watching)
        return [TextContent(
            type="text",
            text=f"Watching directories:\n{paths}"
        )]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    global watcher
    from mcp.server.stdio import stdio_server
    
    logger.debug("Starting file watcher server...")
    
    # Initialize the watcher
    watcher = DirectoryWatcher(server)
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.debug("Server streams initialized")
            
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="file-watcher",
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
    finally:
        if watcher:
            watcher.stop()

if __name__ == "__main__":
    asyncio.run(main()) 