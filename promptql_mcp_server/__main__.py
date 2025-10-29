# promptql_mcp_server/__main__.py

import sys
import os
import argparse
import logging
from promptql_mcp_server.server import mcp, config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger("promptql_main")

def main():
    """Main entry point for the PromptQL MCP server."""
    logger.info("="*80)
    logger.info("STARTING PROMPTQL MCP SERVER")
    logger.info("="*80)
    
    parser = argparse.ArgumentParser(description="PromptQL MCP Server")
    subparsers = parser.add_subparsers(dest="command")
    
    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Configure the server")
    setup_parser.add_argument("--api-key", required=True, help="PromptQL API key")
    setup_parser.add_argument("--playground-url", required=True, help="PromptQL playground URL")
    setup_parser.add_argument("--auth-token", required=True, help="DDN Auth Token")

    # Run command (default)
    run_parser = subparsers.add_parser("run", help="Run the server")

    args = parser.parse_args()

    if args.command == "setup":
        config.set("api_key", args.api_key)
        config.set("playground_url", args.playground_url)
        config.set("auth_token", args.auth_token)
        logger.info("Configuration saved successfully.")
        return 0
    
    # Default to running the server
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Check if configuration is set
    api_key = config.get("api_key")
    playground_url = config.get("playground_url")
    auth_token = config.get("auth_token")

    if not api_key or not playground_url or not auth_token:
        logger.warning("WARNING: PromptQL configuration incomplete.")
        logger.warning("You can configure by running:")
        logger.warning("  python -m promptql_mcp_server setup --api-key YOUR_API_KEY --playground-url YOUR_PLAYGROUND_URL --auth-token YOUR_AUTH_TOKEN")
        logger.warning("Or by setting environment variables:")
        logger.warning("  PROMPTQL_API_KEY, PROMPTQL_PLAYGROUND_URL, and PROMPTQL_AUTH_TOKEN")
        logger.warning("Continuing with unconfigured server...")
    else:
        # Show partial credentials for debugging
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if api_key else "None"
        masked_token = f"{auth_token[:8]}...{auth_token[-4:]}" if len(auth_token) > 12 else auth_token[:4] + "..."
        logger.info(f"Using API Key: {masked_key}")
        logger.info(f"Using Playground URL: {playground_url}")
        logger.info(f"Using Auth Token: {masked_token}")
    
    # Run the MCP server
    logger.info("STARTING MCP SERVER - READY FOR CONNECTIONS")
    mcp.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())