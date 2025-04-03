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
- A Hasura PromptQL project with API key and DDN URL
- Claude Desktop (for interactive use) or any MCP-compatible client

### Install from Source

```bash
git clone https://github.com/hasura/promptql-mcp-server.git
cd promptql-mcp-server
pip install -e .
```

## Quick Start

1. Configure your PromptQL credentials:

```bash
python -m promptql_mcp_server setup --api-key YOUR_API_KEY --ddn-url YOUR_DDN_URL
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
      "command": "python",
      "args": ["-m", "promptql_mcp_server"]
    }
  }
}
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
- **ask_question** - Ask natural language questions about your data
- **setup_config** - Configure PromptQL API key and DDN URL
- **check_config** - Verify the current configuration status

### Prompts
- **data_analysis** - Create a specialized prompt for data analysis on a specific topic

## Architecture

This integration follows a client-server architecture:

1. **PromptQL MCP Server** - A Python server that exposes PromptQL capabilities through the MCP protocol
2. **MCP Client** - Any client that implements the MCP protocol (e.g., Claude Desktop)
3. **PromptQL API** - Hasura's Natural Language API for data access and analysis

The server translates between the MCP protocol and PromptQL's API, allowing seamless integration between AI assistants and your enterprise data.

## Development

### Project Structure

```
promptql-mcp-server/
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