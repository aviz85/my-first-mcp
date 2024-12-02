import os
os.environ['TK_SILENCE_DEPRECATION'] = '1'

import asyncio
import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json
from concurrent.futures import ThreadPoolExecutor

class ReminderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reminder Manager")
        self.root.geometry("600x400")
        
        # Setup UI
        self._setup_ui()
        
        # Initialize async stuff
        self.session = None
        self.loop = asyncio.new_event_loop()
        self.thread_pool = ThreadPoolExecutor(max_workers=1)
        
        # Start MCP client
        self.thread_pool.submit(self._start_mcp_client)
        
        # Schedule periodic updates
        self.root.after(1000, self._periodic_update)
    
    def _setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="New Reminder", padding="5")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(input_frame, text="Minutes:").grid(row=0, column=0, padx=5)
        self.minutes_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.minutes_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="Message:").grid(row=0, column=2, padx=5)
        self.message_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.message_var, width=30).grid(row=0, column=3, padx=5)
        
        ttk.Button(input_frame, text="Add Reminder", command=self._add_reminder).grid(row=0, column=4, padx=5)
        
        # List section
        list_frame = ttk.LabelFrame(main_frame, text="Active Reminders", padding="5")
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.reminders_list = ttk.Treeview(list_frame, columns=("id", "time", "message"), show="headings")
        self.reminders_list.heading("id", text="ID")
        self.reminders_list.heading("time", text="Time Left")
        self.reminders_list.heading("message", text="Message")
        self.reminders_list.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Notifications", padding="5")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
    
    def _start_mcp_client(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._init_mcp())
    
    async def _init_mcp(self):
        server_params = StdioServerParameters(
            command="/Users/aviz/my-first-mcp/.venv/bin/python",
            args=["/Users/aviz/my-first-mcp/src/reminder_server/server.py"]
        )
        
        try:
            self._log("Connecting to reminder server...")
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session
                    await session.initialize()
                    self._log("✅ Connected to reminder server")
                    
                    while True:
                        try:
                            notification = await session.get_notification()
                            if notification:
                                self.root.after(0, self._log, f"🔔 {notification.status}")
                        except Exception as e:
                            self._log(f"Notification error: {str(e)}")
                        await asyncio.sleep(0.1)
        except Exception as e:
            self._log(f"Connection error: {str(e)}")
    
    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def _add_reminder(self):
        minutes = self.minutes_var.get()
        message = self.message_var.get()
        
        if not minutes or not message:
            self._log("❌ Please fill in both minutes and message")
            return
        
        try:
            minutes = int(minutes)
            if minutes <= 0:
                raise ValueError("Minutes must be positive")
        except ValueError:
            self._log("❌ Minutes must be a positive number")
            return
        
        if self.session:
            asyncio.run_coroutine_threadsafe(
                self._async_add_reminder(minutes, message),
                self.loop
            )
        else:
            self._log("❌ Not connected to server")
    
    async def _async_add_reminder(self, minutes: int, message: str):
        try:
            result = await self.session.call_tool(
                "set_reminder",
                arguments={
                    "minutes": minutes,
                    "message": message
                }
            )
            self.root.after(0, self._handle_add_result, result, minutes, message)
        except Exception as e:
            self.root.after(0, self._log, f"❌ Error: {str(e)}")
    
    def _handle_add_result(self, result, minutes, message):
        self._log(f"✅ Reminder set for {minutes} minutes: {message}")
        self.minutes_var.set("")
        self.message_var.set("")
        self._update_reminders()
    
    def _update_reminders(self):
        if self.session:
            asyncio.run_coroutine_threadsafe(self._async_update_reminders(), self.loop)
    
    async def _async_update_reminders(self):
        try:
            result = await self.session.call_tool(
                "list_reminders",
                arguments={}
            )
            self.root.after(0, self._update_reminders_list, result)
        except Exception as e:
            self.root.after(0, self._log, f"❌ Error updating reminders: {str(e)}")
    
    def _update_reminders_list(self, result):
        for item in self.reminders_list.get_children():
            self.reminders_list.delete(item)
        
        if hasattr(result, 'content'):
            for item in result.content:
                if hasattr(item, 'text'):
                    lines = item.text.split('\n')[1:]  # Skip header
                    for line in lines:
                        if line.strip():
                            parts = line.replace('•', '').strip().split(' (', 1)
                            if len(parts) == 2:
                                rid = parts[0]
                                time_str = parts[1].rstrip(')')
                                self.reminders_list.insert('', tk.END, values=(rid, time_str, ""))
    
    def _periodic_update(self):
        self._update_reminders()
        self.root.after(1000, self._periodic_update)  # Update every second

def main():
    root = tk.Tk()
    app = ReminderApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 