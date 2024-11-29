# OS Control MCP Servers

A collection of Model Context Protocol (MCP) servers that let you control your computer by talking naturally with Claude.

## Available Servers

### 1. Calendar Assistant
Manages your Google Calendar - just tell Claude what you want to do with your calendar (works on all operating systems).

### 2. Mac Control
Controls your Mac - just describe what you want to do in natural language (macOS only).

### 3. Windows Control
Controls your Windows PC - just tell Claude what you want to do (Windows only).

## Important Note ⚠️
Configure only the servers appropriate for your operating system:
- On macOS: Use Calendar and Mac Control servers only
- On Windows: Use Calendar and Windows Control servers only
- Do not configure both Mac and Windows servers on the same machine

## Examples

### Calendar Assistant
Just tell Claude what you want:
- "Schedule a team meeting for tomorrow at 2pm"
- "What's my next meeting?"
- "When am I free today?"
- "Cancel my next meeting"

### Mac Control
Tell Claude naturally:
- "Turn down the volume to 50%"
- "Send me a notification in 30 minutes to take a break"
- "What processes are running right now?"
- "Show me all my Chrome windows"

### Windows Control
Just ask Claude:
- "Lock my computer"
- "Take a screenshot"
- "What's using the most CPU right now?"
- "Show me what's in my Downloads folder"

## How It Works
1. Just chat with Claude normally
2. Tell it what you want to do with your computer
3. Claude will understand and use the appropriate commands behind the scenes

No need to remember specific commands or syntax - Claude handles that for you!

## Setup

1. Install dependencies:
```bash
uv pip install -e .
# or
pip install -r requirements.txt
```

2. Configure Claude Desktop based on your OS:

### For macOS:
```json
{
  "mcpServers": {
    "calendar": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/src/calendar_assistant/server.py"]
    },
    "mac": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/src/mac_control/server.py"]
    }
  }
}
```

### For Windows:
```json
{
  "mcpServers": {
    "calendar": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\src\\calendar_assistant\\server.py"]
    },
    "win": {
      "command": "C:\\path\\to\\venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\src\\win_control\\server.py"]
    }
  }
}
```

Config file locations:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

## Project Structure

```
.
├── src/
│   ├── calendar_assistant/
│   │   ├── __init__.py
│   │   └── server.py
│   ├── mac_control/
│   │   ├── __init__.py
│   │   └── server.py
│   └── win_control/
│       ├── __init__.py
│       └── server.py
├── credentials.json
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Setup Notes

### Calendar Assistant
- Requires Google Calendar API credentials
- Place `credentials.json` in project root
- Will authenticate on first run

### Mac Control
- Requires macOS
- Uses AppleScript and shell commands
- No additional setup needed

### Windows Control
- Requires Windows
- Uses PowerShell and CMD
- Requires admin rights for some commands

## Security Notes

- Never commit sensitive files (`credentials.json`, `token.json`)
- Be careful with shell/PowerShell commands
- Review scripts before execution
- Use with trusted input only

## Troubleshooting

1. **Server Connection Issues**:
   - Check paths in `claude_desktop_config.json`
   - Ensure Python virtual environment is activated
   - Check logs in `/tmp/` or `%APPDATA%\Local\`

2. **Permission Issues**:
   - Run as admin for certain Windows commands
   - Check file permissions
   - Verify API access for Calendar

3. **Command Failures**:
   - Check log files for detailed errors
   - Verify command syntax
   - Check system requirements

## License

MIT License - See LICENSE file for details 