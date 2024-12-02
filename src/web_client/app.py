import streamlit as st
import asyncio
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json
from concurrent.futures import ThreadPoolExecutor

class ReminderClient:
    def __init__(self):
        self.session = None
        self.loop = asyncio.new_event_loop()
        self.thread_pool = ThreadPoolExecutor(max_workers=1)
        self.initialized = False
        self._start_client()
    
    def _start_client(self):
        self.thread_pool.submit(self._run_async_client)
    
    def _run_async_client(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._init_mcp())
    
    async def _init_mcp(self):
        server_params = StdioServerParameters(
            command="/Users/aviz/my-first-mcp/.venv/bin/python",
            args=["/Users/aviz/my-first-mcp/src/reminder_server/server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session
                    await session.initialize()
                    self.initialized = True
                    
                    # Listen for notifications using the notification stream
                    async for notification in session.notification_stream():
                        try:
                            if 'notifications' not in st.session_state:
                                st.session_state.notifications = []
                            
                            # Extract message from notification
                            message = None
                            if hasattr(notification, 'params'):
                                message = notification.params.get('message', str(notification))
                            else:
                                message = str(notification)
                            
                            st.session_state.notifications.append({
                                'time': datetime.now().strftime("%H:%M:%S"),
                                'message': message
                            })
                        except Exception as e:
                            print(f"Notification processing error: {str(e)}")
                            await asyncio.sleep(1)
                        
                        await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Connection error: {str(e)}")
            await asyncio.sleep(5)
            await self._init_mcp()
    
    def add_reminder(self, minutes: int, message: str):
        if not self.session or not self.initialized:
            return "Server not ready, please wait...", False
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._async_add_reminder(minutes, message),
                self.loop
            )
            result = future.result(timeout=5)
            return "Reminder added successfully!", True
        except Exception as e:
            return f"Error: {str(e)}", False
    
    async def _async_add_reminder(self, minutes: int, message: str):
        return await self.session.call_tool(
            "set_reminder",
            arguments={
                "minutes": minutes,
                "message": message
            }
        )
    
    def list_reminders(self):
        if not self.session or not self.initialized:
            return []
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._async_list_reminders(),
                self.loop
            )
            result = future.result(timeout=5)
            if hasattr(result, 'content'):
                for item in result.content:
                    if hasattr(item, 'text'):
                        lines = item.text.split('\n')[1:]
                        reminders = []
                        for line in lines:
                            if line.strip():
                                parts = line.replace('•', '').strip().split(' (', 1)
                                if len(parts) == 2:
                                    rid = parts[0]
                                    time_str = parts[1].rstrip(')')
                                    reminders.append({
                                        'id': rid,
                                        'time': time_str
                                    })
                        return reminders
            return []
        except Exception as e:
            print(f"Error listing reminders: {str(e)}")
            return []
    
    async def _async_list_reminders(self):
        return await self.session.call_tool(
            "list_reminders",
            arguments={}
        )

# Initialize the client
if 'client' not in st.session_state:
    st.session_state.client = ReminderClient()

# App title
st.title('⏰ Reminder Manager')

# Connection status
if not st.session_state.client.initialized:
    st.warning("⏳ Connecting to server...")

# Add reminder section
with st.form("new_reminder"):
    st.subheader("Add New Reminder")
    col1, col2 = st.columns([1, 3])
    
    with col1:
        minutes = st.number_input("Minutes", min_value=1, value=5)
    with col2:
        message = st.text_input("Message")
    
    submitted = st.form_submit_button("Add Reminder")
    if submitted:
        msg, success = st.session_state.client.add_reminder(minutes, message)
        if success:
            st.success(msg)
        else:
            st.error(msg)

# Active reminders section
st.subheader("Active Reminders")
reminders = st.session_state.client.list_reminders()
if reminders:
    for reminder in reminders:
        st.info(f"🔔 {reminder['id']} ({reminder['time']})")
else:
    st.write("No active reminders")

# Notifications section
st.subheader("Notifications")
if 'notifications' in st.session_state and st.session_state.notifications:
    for notification in reversed(st.session_state.notifications[-5:]):  # Show last 5
        st.success(f"[{notification['time']}] {notification['message']}")

# Auto-refresh
st.empty()
st.rerun()  # Use rerun() instead of experimental_rerun() 