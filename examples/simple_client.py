import asyncio
import traceback
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    """Simple example client for PromptQL MCP server."""
    
    # Define server parameters
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "promptql_mcp_server"],
        env=None
    )
    
    print("Connecting to PromptQL MCP server...")
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as client:
                # Initialize the connection
                await client.initialize()

                # List available tools
                print("\nListing available tools:")
                tools = await client.list_tools()
                print("\nRaw tools response:", tools)  # Debugging: Print raw response

                for tool in tools:
                    if isinstance(tool, tuple) and len(tool) >= 2:
                        print(f"- {tool[0]}: {tool[1]}")
                    else:
                        print(f"Unexpected tool format: {tool}")
            
                # Set up configuration (if needed)
                setup_config = input("\nDo you want to set up the server configuration? (y/n): ")
                if setup_config.lower() == 'y':
                    api_key = input("Enter your PromptQL API key: ")
                    playground_url = input("Enter your PromptQL playground URL: ")
                    auth_token = input("Enter your DDN Auth Token: ")

                    result = await client.call_tool("setup_config", {
                        "api_key": api_key,
                        "playground_url": playground_url,
                        "auth_token": auth_token
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

    except Exception as e:
        print(f"Error occurred: {e}")
        print(traceback.format_exc())  

if __name__ == "__main__":
    asyncio.run(main())
