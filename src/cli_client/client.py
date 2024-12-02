from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import json
from datetime import datetime, timedelta

def format_time_until(end_time: datetime) -> str:
    """Format time until reminder in a nice way"""
    now = datetime.now()
    diff = end_time - now
    
    if diff.total_seconds() < 0:
        return "Due any moment!"
    
    minutes = int(diff.total_seconds() / 60)
    if minutes < 1:
        return "Less than a minute"
    elif minutes == 1:
        return "1 minute"
    else:
        return f"{minutes} minutes"

def format_result(result):
    """Format the result in a nice way"""
    if hasattr(result, 'content'):
        for item in result.content:
            if hasattr(item, 'text'):
                text = item.text
                if text.startswith('✅'):
                    print("\n" + "="*50)
                    print("SUCCESS!")
                    print("="*50)
                    print(text.replace('✅', '').strip())
                    print("="*50)
                elif text.startswith('❌'):
                    print("\n" + "="*50)
                    print("ERROR!")
                    print("="*50)
                    print(text.replace('❌', '').strip())
                    print("="*50)
                elif "Active reminders" in text:
                    print("\n" + "="*50)
                    print("ACTIVE REMINDERS")
                    print("="*50)
                    reminders = text.split('\n')[1:]  # Skip the header
                    for reminder in reminders:
                        # Already formatted nicely from the server
                        print(f" {reminder.replace('•', '').strip()}")
                    print("="*50)
                else:
                    print(text)
    else:
        print(result)

# Store active reminders and their end times
active_reminders = {}

async def handle_notifications(session):
    """Handle notifications from the server"""
    try:
        while True:  # Keep running until cancelled
            try:
                # Get notification using the notification method
                notification = await session.get_notification()
                if notification:
                    # Print notification in a nice format
                    print("\n" + "="*50)
                    print("🔔 REMINDER")
                    print("="*50)
                    if hasattr(notification, 'status'):
                        print(notification.status)
                    else:
                        print(str(notification))
                    print("="*50)
                    
                    # Reprint menu
                    print("\nWhat would you like to do?")
                    print("1. Set new reminder")
                    print("2. List active reminders")
                    print("3. Cancel a reminder")
                    print("4. Exit")
                    print("Choice > ", end='', flush=True)
                
                # Small delay to prevent CPU hogging
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Notification error: {str(e)}")
                await asyncio.sleep(1)  # Longer delay on error
                
    except asyncio.CancelledError:
        pass  # Clean exit

async def main():
    global active_reminders
    
    print("\n" + "="*50)
    print("REMINDER MANAGER")
    print("="*50)
    
    server_params = StdioServerParameters(
        command="/Users/aviz/my-first-mcp/.venv/bin/python",
        args=["/Users/aviz/my-first-mcp/src/reminder_server/server.py"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Start notification handler task
            notification_task = asyncio.create_task(handle_notifications(session))

            tools = await session.list_tools()
            print("\nAvailable commands:")
            print("-"*30)
            for tool in tools:
                if isinstance(tool, tuple) and tool[0] == 'tools':
                    for t in tool[1]:
                        print(f"📌 {t.name}: {t.description}")

            while True:
                print("\n" + "-"*30)
                print("What would you like to do?")
                print("-"*30)
                print("1. Set new reminder")
                print("2. List active reminders")
                print("3. Cancel a reminder")
                print("4. Exit")
                print("-"*30)
                
                choice = input("Choice > ")

                try:
                    if choice == "1":
                        print("\nSetting new reminder:")
                        print("-"*30)
                        minutes = int(input("Minutes from now > "))
                        message = input("Reminder message > ")
                        
                        result = await session.call_tool(
                            "set_reminder",
                            arguments={
                                "minutes": minutes,
                                "message": message
                            }
                        )
                        # Store end time for new reminder
                        if hasattr(result, 'content'):
                            for item in result.content:
                                if hasattr(item, 'text') and 'ID: ' in item.text:
                                    rid = item.text.split('ID: ')[1].strip()
                                    end_time = datetime.now() + timedelta(minutes=minutes)
                                    active_reminders[rid] = end_time
                        
                        format_result(result)

                    elif choice == "2":
                        result = await session.call_tool(
                            "list_reminders",
                            arguments={}
                        )
                        format_result(result)

                    elif choice == "3":
                        print("\nCancelling reminder:")
                        print("-"*30)
                        task_id = input("Reminder ID to cancel > ")
                        result = await session.call_tool(
                            "cancel_reminder",
                            arguments={"task_id": task_id}
                        )
                        format_result(result)

                    elif choice == "4":
                        print("\nGoodbye! 👋")
                        notification_task.cancel()
                        break

                except Exception as e:
                    print("\n" + "="*50)
                    print("ERROR OCCURRED!")
                    print("="*50)
                    print(f"Error: {str(e)}")
                    print("="*50)

if __name__ == "__main__":
    asyncio.run(main()) 