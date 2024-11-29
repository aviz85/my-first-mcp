# Calendar Assistant MCP

A Model Context Protocol (MCP) server for Google Calendar integration, allowing AI assistants to manage your calendar efficiently.

## Setup

1. Install dependencies:
```bash
uv pip install -e .
# or
pip install -r requirements.txt
```

2. Set up Google Calendar API:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable Google Calendar API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download `credentials.json` to project root

3. Configure Claude Desktop:
```json
{
  "mcpServers": {
    "calendar": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/src/calendar_assistant/server.py"]
    }
  }
}
```
Replace paths with your actual paths:
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

## Usage

Available commands:

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

3. Cancel next meeting:
```
/mcp calendar call cancel_next {
  "notify": true
}
```

4. Find free time today:
```
/mcp calendar call free_today {
  "min_duration": 30
}
```

5. View today's events:
```
/mcp calendar read calendar://events/today
```

## First Run

On first run, the server will:
1. Look for `credentials.json` in project root
2. Open browser for Google OAuth authentication
3. Save authentication token as `token.json`

## Troubleshooting

1. **Authentication Issues**:
   - Ensure `credentials.json` is in project root
   - Delete `token.json` and re-authenticate if needed
   - Check logs at `/tmp/calendar_assistant.log`

2. **Connection Issues**:
   - Verify paths in `claude_desktop_config.json`
   - Ensure Python virtual environment is activated
   - Check Claude Desktop is running

3. **Permission Issues**:
   - Make sure your Google account is added as a test user
   - Enable necessary Calendar API scopes
   - Check Google Cloud Console for API quotas

## Project Structure

```
.
├── src/
│   └── calendar_assistant/
│       ├── __init__.py
│       └── server.py
├── credentials.json
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Security Note

- Never commit `credentials.json` or `token.json`
- Keep your Google Cloud project credentials secure
- Review OAuth consent screen settings regularly

## License

MIT License - See LICENSE file for details 