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

- Python 3.10 or higher (for local installation) OR Docker (for containerized installation)
- A Hasura PromptQL project with API key and DDN URL
- Claude Desktop (for interactive use) or any MCP-compatible client

### Option 1: Using Docker (Recommended)

The easiest way to run the PromptQL MCP server is using Docker:

```bash
# Build the Docker image
docker build -t promptql-mcp:latest .

# Or use the pre-built image from Docker Hub (coming soon)
docker pull yourusername/promptql-mcp:latest
```

See the [Docker Setup Guide](docker/README.md) for detailed instructions.

### Option 2: Install from Source

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
python -m promptql_mcp_server setup --api-key YOUR_PROMPTQL_API_KEY --ddn-url YOUR_DDN_URL
```

2. Test the server:

```bash
python -m promptql_mcp_server
```

3. In a new terminal, try the example client:

```bash
python examples/simple_client.py
```

## Using with Claude Desktop or Cursor

1. Install [Claude Desktop](https://claude.ai/download) or have Cursor installed
2. Open the MCP configuration file:

   - **Claude Desktop**: Settings > Developer > Edit Config
   - **Cursor**: `~/.cursor/mcp.json`

3. Add the configuration:

### Using Docker (Recommended)

```json
{
  "mcpServers": {
    "promptql": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "PROMPTQL_API_KEY=your_api_key_here",
        "-e",
        "PROMPTQL_DDN_URL=your_ddn_url_here",
        "hasura/promptql-mcp:latest"
      ]
    }
  }
}
```

### Using Local Python Installation

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

If you're using a virtual environment:

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

4. Restart Claude Desktop or Cursor
5. Chat with Claude/Cursor and use natural language to query your data

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
