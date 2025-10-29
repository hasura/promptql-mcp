# PromptQL MCP Server

Connect [Hasura PromptQL](https://hasura.io/promptql/) to AI assistants like Claude using the Model Context Protocol (MCP).

## Overview

This project provides a bridge between Hasura's PromptQL data agent and AI assistants through the Model Context Protocol. With this integration, AI assistants can directly query your enterprise data using natural language, leveraging PromptQL's powerful capabilities for data access, analysis, and visualization.

## Features

- 🔍 **Natural Language Data Queries** - Ask questions about your enterprise data in plain English
- 📊 **Table Artifact Support** - Get formatted table results from your data queries
- 🔐 **Secure Configuration** - Safely store and manage your PromptQL API credentials
- 📈 **Data Analysis** - Get insights and visualizations from your data
- 🛠️ **Simple Integration** - Works with Claude Desktop and other MCP-compatible clients

## Installation

### Prerequisites

- Python 3.10 or higher
- A Hasura PromptQL project with API key, playground URL, and DDN Auth Token
- Claude Desktop (for interactive use) or any MCP-compatible client

### Install from Source

1. Clone the repository:
```bash
git clone https://github.com/hasura/promptql-mcp.git
cd promptql-mcp
```

2. Set up a virtual environment (recommended):
```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the package:
```bash
pip install -e .
```

## Quick Start

1. Configure your PromptQL credentials:

```bash
python -m promptql_mcp_server setup --api-key YOUR_PROMPTQL_API_KEY --playground-url YOUR_PLAYGROUND_URL --auth-token YOUR_AUTH_TOKEN
```

2. Test the server:

```bash
python -m promptql_mcp_server
```

3. In a new terminal, try the example client:

```bash
python examples/simple_client.py
```

## Using with Claude Desktop

1. Install [Claude Desktop](https://claude.ai/download)
2. Open Claude Desktop and go to Settings > Developer
3. Click "Edit Config" and add the following:

```json
{
  "mcpServers": {
    "promptql": {
      "command": "/full/path/to/python",
      "args": ["-m", "promptql_mcp_server"]
    }
  }
}
```

Replace `/full/path/to/python` with the actual path to your Python executable. 

If you're using a virtual environment (recommended):
```json
{
  "mcpServers": {
    "promptql": {
      "command": "/path/to/your/project/venv/bin/python",
      "args": ["-m", "promptql_mcp_server"]
    }
  }
}
```

To find your Python path, run:
```bash
which python  # On macOS/Linux
where python  # On Windows
```

4. Restart Claude Desktop
5. Chat with Claude and use natural language to query your data

### Example Prompts for Claude

- "What were our total sales last quarter?"
- "Who are our top five customers by revenue?"
- "Show me the trend of new user signups over the past 6 months"
- "Which products have the highest profit margin?"

## Available Tools and Prompts

### Tools
The server exposes the following MCP tools:

### Thread Management Mode
- **start_thread** - Start a new conversation thread with an initial message and wait for completion (returns thread_id, interaction_id, and response)
- **start_thread_without_polling** - Start a new conversation thread without waiting for completion (returns thread_id and interaction_id immediately)
- **continue_thread** - Continue an existing thread with a new message (maintains conversation context)
- **get_thread_status** - Check the status of a thread (processing/complete) using GET /threads/v2/{thread_id}
- **cancel_thread** - Cancel the processing of the latest interaction in a thread

### Configuration
- **setup_config** - Configure PromptQL API key, playground URL, and DDN Auth Token
- **check_config** - Verify the current configuration status

## Usage Examples

### Multi-Turn Conversation Mode

#### Option 1: Start with polling (get immediate response)
```python
# Start a new conversation thread (waits for completion and returns full response)
thread_result = await client.call_tool("start_thread", {
    "message": "What tables are available in my database?"
})

# Extract thread_id from result (format: "Thread ID: abc-123\nInteraction ID: def-456\n\n[response content]")
thread_id = thread_result.split("Thread ID: ")[1].split("\n")[0].strip()

# Continue the conversation with context
result = await client.call_tool("continue_thread", {
    "thread_id": thread_id,
    "message": "Show me the schema of the users table"
})
```

#### Option 2: Start without polling (check status separately)
```python
# Start a new conversation thread (returns immediately with thread_id)
thread_result = await client.call_tool("start_thread_without_polling", {
    "message": "What tables are available in my database?"
})

# Extract thread_id from result (format: "Thread ID: abc-123\nInteraction ID: def-456\n\n...")
thread_id = thread_result.split("Thread ID: ")[1].split("\n")[0].strip()

# Check status manually
status_result = await client.call_tool("get_thread_status", {
    "thread_id": thread_id
})

# Continue when ready
result = await client.call_tool("continue_thread", {
    "thread_id": thread_id,
    "message": "Show me the schema of the users table"
})

# Continue further
result = await client.call_tool("continue_thread", {
    "thread_id": thread_id,
    "message": "How many records are in that table?"
})

# Check thread status
status = await client.call_tool("get_thread_status", {
    "thread_id": thread_id
})

# Cancel thread processing (if currently processing)
cancel_result = await client.call_tool("cancel_thread", {
    "thread_id": thread_id
})
```

### With System Instructions
```python
# Start thread with system instructions
result = await client.call_tool("start_thread", {
    "message": "Show me the top 10 products by revenue",
    "system_instructions": "Format all results as markdown tables"
})
```

### Prompts
- **data_analysis** - Create a specialized prompt for data analysis on a specific topic

## Architecture

This integration follows a client-server architecture:

1. **PromptQL MCP Server** - A Python server that exposes PromptQL capabilities through the MCP protocol
2. **MCP Client** - Any client that implements the MCP protocol (e.g., Claude Desktop)
3. **PromptQL API** - Hasura's Natural Language API for data access and analysis

The server translates between the MCP protocol and PromptQL's API, allowing seamless integration between AI assistants and your enterprise data.

## Troubleshooting

### Command not found: pip or python
On many systems, especially macOS, you may need to use `python3` and `pip3` instead of `python` and `pip`.

### externally-managed-environment error
Modern Python installations often prevent global package installation. Use a virtual environment as described in the installation section.

### No module named promptql_mcp_server
Ensure you've:
1. Installed the package with `pip install -e .`
2. Are using the correct Python environment (if using a virtual environment, make sure it's activated)
3. Configured Claude Desktop to use the correct Python executable path

### Python version issues
If you have multiple Python versions installed, make sure you're using Python 3.10 or higher:
```bash
python3.10 -m venv venv  # Specify the exact version
```

## Development

### Project Structure

```
promptql-mcp/
├── promptql_mcp_server/     # Main package
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── server.py            # MCP server implementation
│   ├── config.py            # Configuration management
│   └── api/                 # API clients
│       ├── __init__.py
│       └── promptql_client.py # PromptQL API client
├── examples/                # Example clients
│   └── simple_client.py     # Simple MCP client
├── setup.py                 # Package configuration
└── README.md                # Documentation
```

### Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- [Hasura](https://hasura.io/) for creating PromptQL
- [Anthropic](https://www.anthropic.com/) for developing the Model Context Protocol


## TODO
- process the thread response properly based on interaction_id returned as part of continue_thread and start_thread in mcp_server, at the moment, it only looks for the latest interaction_id
- process the interaction_response accordingly to figure out the code, plan and code_output
- ensure the simple_client.py shows the cancellation_thread demo properly, the current status call looks to be blocking 
- Validate if the artifacts are processed accordingly