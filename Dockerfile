# Dockerfile for PromptQL MCP Server
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy dependency files
COPY setup.py README.md LICENSE ./
COPY promptql_mcp_server/ ./promptql_mcp_server/

# Install dependencies
RUN pip install --no-cache-dir -e .

# Create config directory
RUN mkdir -p /root/.promptql-mcp

# Expose environment variables for configuration
ENV PROMPTQL_API_KEY="" \
    PROMPTQL_DDN_URL=""

# Run the MCP server
ENTRYPOINT ["python", "-m", "promptql_mcp_server"]

