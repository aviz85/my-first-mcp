# OS Control MCP Servers

A collection of Model Context Protocol (MCP) servers for controlling different operating systems through Claude.

## Available Servers

### 1. Calendar Assistant
Manages Google Calendar events and meetings (works on all operating systems).

### 2. Mac Control
Controls macOS system functions using AppleScript and shell commands (macOS only).

### 3. Windows Control
Controls Windows system functions using PowerShell and CMD commands (Windows only).

## Important Note ⚠️
Configure only the servers appropriate for your operating system:
- On macOS: Use Calendar and Mac Control servers only
- On Windows: Use Calendar and Windows Control servers only
- Do not configure both Mac and Windows servers on the same machine

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

## Usage

### Calendar Commands

1. Quick add event:
```
/mcp calendar call quick_add {
  "text": "Team meeting tomorrow at 2pm"
}
```

2. Show next meeting:
```
/mcp calendar call next {}
```

3. Find free time:
```
/mcp calendar call free_today {
  "min_duration": 30
}
```

### Mac Control Commands

1. Run AppleScript:
```
/mcp mac call applescript {
  "script": "tell application \"System Events\" to get name of every process"
}
```

2. Control volume:
```
/mcp mac call volume {
  "level": 50
}
```

3. Send notification:
```
/mcp mac call notification {
  "title": "Hello",
  "message": "Time for a break!"
}
```

### Windows Control Commands

1. Run PowerShell:
```
/mcp win call powershell {
  "script": "Get-Process | Select-Object -First 5"
}
```

2. Run CMD:
```
/mcp win call cmd {
  "command": "dir C:\\"
}
```

3. Lock Windows:
```
/mcp win call lock {}
```

4. Take screenshot:
```
/mcp win call screenshot {
  "path": "C:\\Users\\YourName\\Desktop\\shot.png"
}
```

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