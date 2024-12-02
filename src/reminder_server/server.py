import asyncio
import logging
from datetime import datetime, timedelta
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent
from typing import Any, Sequence
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/reminder_server.log',
    filemode='w'
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("reminder-server")

class ReminderManager:
    def __init__(self, server: Server):
        self.server = server
        self.reminders = {}  # task_id -> (task, end_time)

    async def add_reminder(self, minutes: int, message: str) -> str:
        task_id = f"reminder_{len(self.reminders)}"
        end_time = datetime.now() + timedelta(minutes=minutes)
        
        async def reminder_task():
            await asyncio.sleep(minutes * 60)
            await self.server.notify_status(f"⏰ Reminder: {message}")
            del self.reminders[task_id]
        
        self.reminders[task_id] = (asyncio.create_task(reminder_task()), end_time)
        return task_id

    def list_active(self) -> list[tuple[str, datetime]]:
        return [(tid, end_time) for tid, (_, end_time) in self.reminders.items()]

    def cancel_reminder(self, task_id: str) -> bool:
        if task_id in self.reminders:
            task, _ = self.reminders[task_id]
            task.cancel()
            del self.reminders[task_id]
            return True
        return False

    def stop_all(self):
        for task, _ in self.reminders.values():
            task.cancel()
        self.reminders.clear()

# Global reminder manager
reminder_mgr = None

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="set_reminder",
            description="Set a reminder for X minutes from now",
            inputSchema={
                "type": "object",
                "properties": {
                    "minutes": {
                        "type": "integer",
                        "description": "Minutes from now",
                        "minimum": 1
                    },
                    "message": {
                        "type": "string",
                        "description": "Reminder message"
                    }
                },
                "required": ["minutes", "message"]
            }
        ),
        Tool(
            name="cancel_reminder",
            description="Cancel a specific reminder",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Reminder ID to cancel"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="list_reminders",
            description="List all active reminders",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    global reminder_mgr
    
    if name == "set_reminder":
        minutes = arguments["minutes"]
        message = arguments["message"]
        task_id = await reminder_mgr.add_reminder(minutes, message)
        
        return [TextContent(
            type="text",
            text=f"✅ Reminder set! Will notify in {minutes} minutes\nID: {task_id}"
        )]
    
    elif name == "cancel_reminder":
        task_id = arguments["task_id"]
        if reminder_mgr.cancel_reminder(task_id):
            return [TextContent(
                type="text",
                text=f"✅ Cancelled reminder: {task_id}"
            )]
        else:
            return [TextContent(
                type="text",
                text=f"❌ Reminder not found: {task_id}"
            )]
    
    elif name == "list_reminders":
        reminders = reminder_mgr.list_active()
        if not reminders:
            return [TextContent(
                type="text",
                text="No active reminders"
            )]
        
        formatted_reminders = []
        for rid, end_time in reminders:
            time_left = (end_time - datetime.now()).total_seconds() / 60
            if time_left < 1:
                time_str = "Due any moment!"
            elif time_left < 2:
                time_str = "Due in 1 minute"
            else:
                time_str = f"Due in {int(time_left)} minutes"
            
            formatted_reminders.append(f"• {rid} ({time_str})")
        
        return [TextContent(
            type="text",
            text="Active reminders:\n" + "\n".join(formatted_reminders)
        )]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    global reminder_mgr
    from mcp.server.stdio import stdio_server
    
    logger.debug("Starting reminder server...")
    
    # Initialize the reminder manager
    reminder_mgr = ReminderManager(server)
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.debug("Server streams initialized")
            
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="reminder-server",
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
        if reminder_mgr:
            reminder_mgr.stop_all()

if __name__ == "__main__":
    asyncio.run(main()) 