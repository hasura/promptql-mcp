# examples/simple_client.py

import asyncio
from mcp.client import create_mcp_client, StdioServerParameters

async def main():
    """Simple example client for PromptQL MCP server."""
    
    # Define server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "promptql_mcp_server"],
        env=None
    )
    
    # Connect to the server
    print("Connecting to PromptQL MCP server...")
    async with create_mcp_client(server_params) as client:
        # List available tools
        print("\nListing available tools:")
        tools = await client.list_tools()
        for tool in tools:
            print(f"- {tool.name}: {tool.description}")
        
        # Set up configuration (if needed)
        setup_config = input("\nDo you want to set up the server configuration? (y/n): ")
        if setup_config.lower() == 'y':
            api_key = input("Enter your PromptQL API key: ")
            ddn_url = input("Enter your DDN URL: ")
            
            result = await client.call_tool("setup_config", {
                "api_key": api_key,
                "ddn_url": ddn_url
            })
            print(f"Configuration result: {result}")
        
        # Ask a question
        while True:
            question = input("\nEnter a question to ask PromptQL (or 'exit' to quit): ")
            if question.lower() == 'exit':
                break
            
            print("Asking question...")
            result = await client.call_tool("ask_question", {
                "question": question
            })
            
            print("\nAnswer:")
            print(result)

if __name__ == "__main__":
    asyncio.run(main())