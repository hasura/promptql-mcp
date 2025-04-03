# promptql_mcp_server/__main__.py

import sys
import os
import argparse
import logging
import time
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
    setup_parser.add_argument("--ddn-url", required=True, help="DDN URL")
    
    # Run command (default)
    run_parser = subparsers.add_parser("run", help="Run the server")
    
    args = parser.parse_args()
    
    if args.command == "setup":
        config.set("api_key", args.api_key)
        config.set("ddn_url", args.ddn_url)
        logger.info("Configuration saved successfully.")
        return 0
    
    # Default to running the server
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Check if configuration is set
    api_key = config.get("api_key")
    ddn_url = config.get("ddn_url")
    
    if not api_key or not ddn_url:
        logger.warning("WARNING: PromptQL API key or DDN URL not configured.")
        logger.warning("You can configure them by running:")
        logger.warning("  python -m promptql_mcp_server setup --api-key YOUR_API_KEY --ddn-url YOUR_DDN_URL")
        logger.warning("Or by setting environment variables:")
        logger.warning("  PROMPTQL_API_KEY and PROMPTQL_DDN_URL")
        logger.warning("Continuing with unconfigured server...")
    else:
        # Show partial key for debugging
        masked_key = f"{api_key[:8]}...{api_key[-4:]}" if api_key else "None"
        logger.info(f"Using API Key: {masked_key}")
        logger.info(f"Using DDN URL: {ddn_url}")
    
    # Run the MCP server
    logger.info("STARTING MCP SERVER - READY FOR CONNECTIONS")
    mcp.run()
    return 0

if __name__ == "__main__":
    sys.exit(main())