import streamlit as st
import asyncio
from datetime import datetime
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from concurrent.futures import ThreadPoolExecutor
import os
import time
class AIAssistant:
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
            args=["/Users/aviz/my-first-mcp/src/code_analyzer/server.py"]
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
    
    async def _ask_ai(self, user_message: str):
        # Get current context first
        context = await self.session.call_tool(
            "get_context",
            arguments={}
        )
        
        # Create sampling request with context
        request = {
            "messages": [
                {
                    "role": "system",
                    "content": {
                        "type": "text",
                        "text": """You are a helpful coding assistant that can analyze Python code.
                                 You have access to code analysis tools and can help users understand code structure.
                                 Current context:
                                 """ + str(context)
                    }
                },
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": user_message
                    }
                }
            ],
            "includeContext": "thisServer",
            "maxTokens": 1000
        }
        
        # Send sampling request using the sampling API
        response = await self.session.sampling.create_message(request)
        
        # Extract text from response
        if response and hasattr(response, 'content'):
            if isinstance(response.content, dict) and 'text' in response.content:
                return response.content['text']
            elif hasattr(response.content, 'text'):
                return response.content.text
        return None
    
    def ask(self, question: str):
        if not self.session or not self.initialized:
            return "System not ready, please wait..."
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self._ask_ai(question),
                self.loop
            )
            result = future.result(timeout=10)
            return result or "Sorry, I couldn't process that request."
        except Exception as e:
            return f"Error: {str(e)}"

# Initialize the assistant
if 'assistant' not in st.session_state:
    st.session_state.assistant = AIAssistant()
    st.session_state.messages = []

# App title and styling
st.set_page_config(page_title="AI File Assistant", page_icon="🤖")
st.markdown("""
    <style>
        .chat-message {
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .user-message {
            background-color: #e6f3ff;
        }
        .assistant-message {
            background-color: #f0f2f6;
        }
    </style>
""", unsafe_allow_html=True)

st.title('🤖 AI File Assistant')

# Connection status
if not st.session_state.assistant.initialized:
    st.warning("⏳ Connecting to system...")

# Chat interface
st.subheader("Chat")

# Display chat history
for message in st.session_state.messages:
    with st.container():
        if message["role"] == "user":
            st.markdown(f"""
                <div class="chat-message user-message">
                    <b>You:</b> {message["content"]}
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="chat-message assistant-message">
                    <b>Assistant:</b> {message["content"]}
                </div>
            """, unsafe_allow_html=True)

# Input form
with st.form("chat_input", clear_on_submit=True):
    user_input = st.text_area("Your message:", height=100)
    submitted = st.form_submit_button(
        "Send", 
        disabled=not st.session_state.assistant.initialized,
        use_container_width=True
    )
    
    if submitted and user_input:
        # Add user message to history
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Get AI response
        response = st.session_state.assistant.ask(user_input)
        
        # Add assistant response to history
        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })
        
        # Rerun to update chat
        st.rerun()

# Auto-refresh for connection status
if not st.session_state.assistant.initialized:
    time.sleep(1)
    st.rerun()

if __name__ == "__main__":
    import sys
    import streamlit.web.bootstrap as bootstrap
    
    # Run Streamlit app
    sys.argv = ["streamlit", "run", __file__]
    bootstrap.run(__file__, '', sys.argv, flag_options={}) 