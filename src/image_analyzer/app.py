import streamlit as st
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from concurrent.futures import ThreadPoolExecutor
import os
from PIL import Image
import io
import time

class ImageAnalyzer:
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
            args=["/Users/aviz/my-first-mcp/src/image_analyzer/server.py"]
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
    
    def analyze_image(self, image_path: str):
        if not self.session or not self.initialized:
            return "System not ready", False
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._analyze_image(image_path),
                self.loop
            )
            result = future.result(timeout=30)  # Longer timeout for image analysis
            return result, True
        except Exception as e:
            return f"Error: {str(e)}", False
    
    async def _analyze_image(self, image_path: str):
        # First load the image
        await self.session.call_tool(
            "analyze_image",
            arguments={"path": image_path}
        )
        
        # Then get the analysis
        result = await self.session.call_tool(
            "get_analysis",
            arguments={}
        )
        
        if hasattr(result, 'content') and len(result.content) > 0:
            return result.content[0].text
        return "Failed to analyze image"

# Initialize analyzer
if 'analyzer' not in st.session_state:
    st.session_state.analyzer = ImageAnalyzer()

# App title and styling
st.set_page_config(page_title="Image Analyzer", page_icon="🖼️", layout="wide")
st.title("🖼️ AI Image Analyzer")

# Connection status
if not st.session_state.analyzer.initialized:
    st.warning("⏳ Connecting to system...")

# File uploader
uploaded_file = st.file_uploader("Choose an image...", type=['png', 'jpg', 'jpeg'])

if uploaded_file is not None:
    # Display image
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Image")
        st.image(uploaded_file)
    
    with col2:
        st.subheader("Analysis")
        
        # Save uploaded file temporarily
        temp_path = f"/tmp/{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # Analyze image
        with st.spinner("Analyzing image..."):
            analysis, success = st.session_state.analyzer.analyze_image(temp_path)
            
            if success:
                st.markdown(analysis)
            else:
                st.error(analysis)
        
        # Clean up
        os.remove(temp_path)

# Auto-refresh for connection status
if not st.session_state.analyzer.initialized:
    time.sleep(1)
    st.rerun() 