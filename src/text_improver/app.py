import streamlit as st
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from concurrent.futures import ThreadPoolExecutor
import time

class TextImprover:
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
            args=["/Users/aviz/my-first-mcp/src/text_improver/server.py"]
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    self.session = session
                    await session.initialize()
                    self.initialized = True
                    while True:
                        await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Connection error: {str(e)}")
            self.initialized = False
            await asyncio.sleep(5)
            await self._init_mcp()
    
    def improve_text(self, text: str, style: str) -> tuple[str, bool]:
        if not self.session or not self.initialized:
            return "System not ready", False
        
        try:
            # Set text first
            future = asyncio.run_coroutine_threadsafe(
                self.session.call_tool("set_text", arguments={"text": text}),
                self.loop
            )
            future.result(timeout=5)
            
            # Then get improvements
            future = asyncio.run_coroutine_threadsafe(
                self.session.call_tool("improve_text", arguments={"style": style}),
                self.loop
            )
            result = future.result(timeout=30)
            
            if hasattr(result, 'content') and len(result.content) > 0:
                return result.content[0].text, True
            return "Failed to get improvements", False
            
        except Exception as e:
            return f"Error: {str(e)}", False

# Initialize improver
if 'improver' not in st.session_state:
    st.session_state.improver = TextImprover()

# App title and styling
st.set_page_config(page_title="Text Improver", page_icon="✍️", layout="wide")
st.title("✍️ AI Text Improver")

# Connection status
if not st.session_state.improver.initialized:
    st.warning("⏳ Connecting to system...")

# Text input
text = st.text_area("Enter your text:", height=200)

# Style selection
style = st.selectbox(
    "Choose improvement style:",
    ["formal", "creative", "concise"],
    format_func=lambda x: {
        "formal": "🎩 Formal",
        "creative": "🎨 Creative",
        "concise": "✂️ Concise"
    }[x]
)

# Improve button
if st.button("Improve Text", disabled=not st.session_state.improver.initialized or not text):
    with st.spinner("Getting improvements..."):
        improvements, success = st.session_state.improver.improve_text(text, style)
        
        if success:
            st.markdown("### Improvements")
            st.markdown(improvements)
        else:
            st.error(improvements)

# Auto-refresh for connection status
if not st.session_state.improver.initialized:
    time.sleep(1)
    st.rerun() 