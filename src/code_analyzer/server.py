import asyncio
import logging
from datetime import datetime
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, Resource
from typing import Any, Sequence
import os
import ast
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='/tmp/code_analyzer.log',
    filemode='w'
)
logger = logging.getLogger(__name__)

# Create server instance
server = Server("code-analyzer")

class CodeAnalyzer:
    def __init__(self):
        self.current_file = None
        self.current_ast = None
    
    def analyze_file(self, file_path: str) -> dict:
        """Analyze a Python file and return its structure"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                self.current_file = content
                self.current_ast = ast.parse(content)
                
                return {
                    'functions': self._get_functions(),
                    'classes': self._get_classes(),
                    'imports': self._get_imports(),
                    'loc': len(content.splitlines()),
                }
        except Exception as e:
            logger.error(f"Error analyzing file: {str(e)}")
            return None
    
    def _get_functions(self) -> list[dict]:
        """Extract function definitions"""
        functions = []
        for node in ast.walk(self.current_ast):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'args': [arg.arg for arg in node.args.args],
                    'line': node.lineno,
                    'doc': ast.get_docstring(node)
                })
        return functions
    
    def _get_classes(self) -> list[dict]:
        """Extract class definitions"""
        classes = []
        for node in ast.walk(self.current_ast):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'bases': [base.id for base in node.bases if isinstance(base, ast.Name)],
                    'methods': [m.name for m in node.body if isinstance(m, ast.FunctionDef)],
                    'line': node.lineno,
                    'doc': ast.get_docstring(node)
                })
        return classes
    
    def _get_imports(self) -> list[str]:
        """Extract imports"""
        imports = []
        for node in ast.walk(self.current_ast):
            if isinstance(node, ast.Import):
                imports.extend(name.name for name in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module}.{node.names[0].name}")
        return imports
    
    def get_code_context(self) -> str:
        """Get current file content and analysis as context"""
        if not self.current_file:
            return "No file loaded"
        
        analysis = self.analyze_file(self.current_file)
        if not analysis:
            return "Failed to analyze file"
        
        return f"""
Current file content:
{self.current_file}

Analysis:
- Functions: {len(analysis['functions'])}
- Classes: {len(analysis['classes'])}
- Imports: {len(analysis['imports'])}
- Lines of code: {analysis['loc']}

Detailed structure:
{json.dumps(analysis, indent=2)}
"""

# Global analyzer instance
analyzer = CodeAnalyzer()

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_file",
            description="Analyze a Python file and return its structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to Python file"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="get_context",
            description="Get current file analysis context",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent]:
    global analyzer
    
    if name == "analyze_file":
        path = arguments["path"]
        result = analyzer.analyze_file(path)
        
        if result:
            return [TextContent(
                type="text",
                text=f"Analysis of {path}:\n" + json.dumps(result, indent=2)
            )]
        else:
            return [TextContent(
                type="text",
                text=f"Failed to analyze {path}"
            )]
    
    elif name == "get_context":
        context = analyzer.get_code_context()
        return [TextContent(
            type="text",
            text=context
        )]
    
    raise ValueError(f"Unknown tool: {name}")

async def main():
    from mcp.server.stdio import stdio_server
    
    logger.debug("Starting code analyzer server...")
    
    try:
        async with stdio_server() as (read_stream, write_stream):
            logger.debug("Server streams initialized")
            
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="code-analyzer",
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