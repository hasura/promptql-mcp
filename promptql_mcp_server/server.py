# promptql_mcp_server/server.py

from mcp.server.fastmcp import FastMCP
from typing import Optional
import logging

from promptql_mcp_server.api.promptql_client import PromptQLClient
from promptql_mcp_server.config import ConfigManager

# Ensure logger is configured to output to stderr
logger = logging.getLogger("promptql_server")

# Initialize configuration
config = ConfigManager()

# Create an MCP server
mcp = FastMCP("PromptQL")

def _get_promptql_client() -> PromptQLClient:
    """Get a configured PromptQL client."""
    api_key = config.get("api_key")
    playground_url = config.get("playground_url")
    auth_token = config.get("auth_token")

    logger.info(f"Loading config - API Key exists: {bool(api_key)}, Playground URL exists: {bool(playground_url)}, Auth Token exists: {bool(auth_token)}")

    if not api_key or not playground_url or not auth_token:
        raise ValueError("PromptQL API key, playground URL, and auth token must be configured. Use the setup_config tool.")

    return PromptQLClient(api_key=api_key, playground_url=playground_url, auth_token=auth_token)

@mcp.tool(name="ask_question")
async def ask_question(question: str, system_instructions: Optional[str] = None) -> str:
    """
    Ask a natural language question to PromptQL.

    Args:
        question: The natural language query to ask
        system_instructions: Optional system instructions for the LLM

    Returns:
        Answer from PromptQL
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: ask_question")
    logger.info(f"Question: '{question}'")
    if system_instructions:
        logger.info(f"System Instructions: '{system_instructions}'")
    logger.info("="*80)
    
    try:
        client = _get_promptql_client()
        
        response = client.query(
            message=question,
            system_instructions=system_instructions
        )

        if "error" in response:
            error_message = f"Error: {response['error']}\n{response.get('details', '')}"
            logger.error(f"ERROR RESPONSE: {error_message}")
            return error_message

        logger.info("PROCESSING PROMPTQL RESPONSE...")

        # Extract the answer from the new thread response format
        answer_text = "No answer received from PromptQL."

        # Look for interactions in the thread state
        interactions = response.get("interactions", [])
        if interactions:
            # Get the latest interaction
            latest_interaction = interactions[-1]
            assistant_actions = latest_interaction.get("assistant_actions", [])

            if assistant_actions:
                # Get the last assistant action with a message (most likely the final response)
                for action in reversed(assistant_actions):
                    if action.get("message"):
                        answer_text = action.get("message", "")
                        break

                # Add plan and code from actions if available
                for action in assistant_actions:
                    # Add plan if available
                    plan = action.get("plan")
                    if plan and "**Execution Plan:**" not in answer_text:
                        logger.info("EXECUTION PLAN FOUND")
                        answer_text += f"\n\n**Execution Plan:**\n{plan}"

                    # Add code if available
                    code = action.get("code")
                    if code and "**Executed Code:**" not in answer_text:
                        logger.info("EXECUTED CODE FOUND")
                        answer_text += f"\n\n**Executed Code:**\n{code}"

                    # Add code output if available
                    code_output = action.get("code_output")
                    if code_output and "**Code Output:**" not in answer_text:
                        logger.info("CODE OUTPUT FOUND")
                        answer_text += f"\n\n**Code Output:**\n{code_output}"
        
        # Process artifacts if available in the new format
        # In the new API, artifacts are referenced by identifier in the thread state
        # We would need to make separate requests to fetch artifact data
        # For now, let's look for artifact identifiers in the response
        artifacts_found = []

        # Look for artifact identifiers in assistant actions
        if interactions:
            for interaction in interactions:
                assistant_actions = interaction.get("assistant_actions", [])
                for action in assistant_actions:
                    # Look for artifact references in the action
                    artifact_identifiers = action.get("artifact_identifiers", [])
                    if artifact_identifiers:
                        artifacts_found.extend(artifact_identifiers)

        if artifacts_found:
            logger.info(f"ARTIFACT IDENTIFIERS FOUND: {len(artifacts_found)}")
            answer_text += f"\n\n**Artifacts Generated:** {', '.join(artifacts_found)}"
            answer_text += "\n\n*Note: Artifact data fetching will be implemented in a future update.*"
        
        logger.info("FINAL ANSWER PREPARED")
        # Log only the beginning of the answer if it's very long
        if len(answer_text) > 1000:
            logger.info(f"ANSWER (truncated): {answer_text[:1000]}...")
        else:
            logger.info(f"ANSWER: {answer_text}")
        
        return answer_text
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"EXCEPTION IN TOOL: {str(e)}")
        logger.error(error_trace)
        return f"An error occurred while processing your question: {str(e)}"

@mcp.tool(name="setup_config")
def setup_config(api_key: str, playground_url: str, auth_token: str) -> str:
    """
    Configure the PromptQL MCP server with API key, playground URL, and auth token.

    Args:
        api_key: PromptQL API key
        playground_url: PromptQL playground URL (e.g., https://promptql.cisco-supplychain-hasura.private-ddn.hasura.app/playground)
        auth_token: DDN Auth Token for accessing your data

    Returns:
        Success message
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: setup_config")
    # Log partial credentials for debugging
    masked_key = api_key[:5] + "..." + api_key[-5:] if api_key else "None"
    masked_token = auth_token[:8] + "..." + auth_token[-4:] if len(auth_token) > 12 else auth_token[:4] + "..."
    logger.info(f"API Key: '{masked_key}' (redacted middle)")
    logger.info(f"Playground URL: '{playground_url}'")
    logger.info(f"Auth Token: '{masked_token}' (redacted middle)")
    logger.info("="*80)

    config.set("api_key", api_key)
    config.set("playground_url", playground_url)
    config.set("auth_token", auth_token)

    logger.info("CONFIGURATION SAVED SUCCESSFULLY")
    return "Configuration saved successfully."

# Add a new tool to check configuration status
@mcp.tool(name="check_config")
def check_config() -> str:
    """
    Check if the PromptQL MCP server is already configured with API key, playground URL, and auth token.

    Returns:
        Configuration status message
    """
    logger.info("="*80)
    logger.info("TOOL CALL: check_config")
    logger.info("="*80)

    api_key = config.get("api_key")
    playground_url = config.get("playground_url")
    auth_token = config.get("auth_token")

    if api_key and playground_url and auth_token:
        masked_key = api_key[:5] + "..." + api_key[-5:] if api_key else "None"
        masked_token = auth_token[:8] + "..." + auth_token[-4:] if len(auth_token) > 12 else auth_token[:4] + "..."
        status = f"PromptQL is configured with:\nAPI Key: {masked_key}\nPlayground URL: {playground_url}\nAuth Token: {masked_token}"
        logger.info("CONFIGURATION CHECK: Already configured")
        return status
    else:
        missing = []
        if not api_key:
            missing.append("API Key")
        if not playground_url:
            missing.append("Playground URL")
        if not auth_token:
            missing.append("Auth Token")

        status = f"PromptQL is not fully configured. Missing: {', '.join(missing)}"
        logger.info(f"CONFIGURATION CHECK: Missing {', '.join(missing)}")
        return status

@mcp.prompt(name="data_analysis")
def data_analysis_prompt(topic: str) -> str:
    """Create a prompt for data analysis on a specific topic."""
    logger.info("="*80)
    logger.info(f"PROMPT: data_analysis")
    logger.info(f"Topic: '{topic}'")
    logger.info("="*80)
    
    prompt = f"""
Please analyze my data related to {topic}. 
Include the following in your analysis:
1. Key trends over time
2. Important correlations
3. Unusual patterns or anomalies
4. Actionable insights
"""
    logger.info(f"Generated prompt: {prompt}")
    
    return prompt