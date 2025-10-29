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



@mcp.tool(name="setup_config")
def setup_config(api_key: str, playground_url: str, auth_token: str) -> str:
    """
    Configure the PromptQL MCP server with API key, playground URL, and auth token.

    Args:
        api_key: PromptQL API key
        playground_url: PromptQL playground URL (e.g., https://promptql.<dataplane-name>.private-ddn.hasura.app/playground)
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

@mcp.tool(name="start_thread")
async def start_thread(message: str, system_instructions: Optional[str] = None) -> str:
    """
    Start a new PromptQL thread with a message and poll for completion.

    Args:
        message: The initial message to start the thread with
        system_instructions: Optional system instructions for the LLM

    Returns:
        Complete response from PromptQL including thread_id, interaction_id, and answer
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: start_thread")
    logger.info(f"Message: '{message}'")
    logger.info("="*80)

    try:
        client = _get_promptql_client()

        result = client.start_thread(
            message=message,
            system_instructions=system_instructions
        )

        if "error" in result:
            error_message = f"Error: {result['error']}\n{result.get('details', '')}"
            logger.error(f"ERROR RESPONSE: {error_message}")
            return error_message

        # Extract thread_id and interaction_id from the result
        thread_id = result.get("thread_id")
        interaction_id = result.get("interaction_id")

        if not thread_id:
            logger.error("No thread_id in response")
            return "Error: No thread_id received from PromptQL"

        logger.info(f"THREAD COMPLETED: {thread_id}")

        # Extract the answer from the thread response format
        answer_text = "No answer received from PromptQL."

        # Look for interactions in the thread state
        interactions = result.get("interactions", [])
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

        # Process artifacts if available
        artifacts_found = []
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

        # Format the final response with thread info and answer
        response_text = f"Thread ID: {thread_id}"
        if interaction_id:
            response_text += f"\nInteraction ID: {interaction_id}"
        response_text += f"\n\n{answer_text}"

        logger.info("FINAL RESPONSE PREPARED")
        return response_text

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        logger.error(error_trace)
        return f"Unexpected error: {str(e)}"

@mcp.tool(name="start_thread_without_polling")
async def start_thread_without_polling(message: str, system_instructions: Optional[str] = None) -> str:
    """
    Start a new PromptQL thread with a message without waiting for completion.

    Args:
        message: The initial message to start the thread with
        system_instructions: Optional system instructions for the LLM

    Returns:
        Thread ID and interaction ID for the started thread
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: start_thread_without_polling")
    logger.info(f"Message: '{message}'")
    logger.info("="*80)

    try:
        client = _get_promptql_client()

        result = client.start_thread_without_polling(
            message=message,
            system_instructions=system_instructions
        )

        if "error" in result:
            error_message = f"Error: {result['error']}\n{result.get('details', '')}"
            logger.error(f"ERROR RESPONSE: {error_message}")
            return error_message

        # Extract thread_id and interaction_id from the result
        thread_id = result.get("thread_id")
        interaction_id = result.get("interaction_id")

        if not thread_id:
            logger.error("No thread_id in response")
            return "Error: No thread_id received from PromptQL"

        logger.info(f"THREAD STARTED (NO POLLING): {thread_id}")

        # Format the response with thread info
        response_text = f"Thread ID: {thread_id}"
        if interaction_id:
            response_text += f"\nInteraction ID: {interaction_id}"
        response_text += f"\n\nThread started successfully. Use get_thread_status to check progress or continue_thread to add more messages."

        logger.info("THREAD START RESPONSE PREPARED")
        return response_text

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        logger.error(error_trace)
        return f"Unexpected error: {str(e)}"

@mcp.tool(name="continue_thread")
async def continue_thread(thread_id: str, message: str, system_instructions: Optional[str] = None) -> str:
    """
    Continue an existing PromptQL thread with a new message.

    Args:
        thread_id: The ID of the thread to continue
        message: The new message to add to the thread
        system_instructions: Optional system instructions for the LLM

    Returns:
        Response from PromptQL for the continued conversation
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: continue_thread")
    logger.info(f"Thread ID: {thread_id}")
    logger.info(f"Message: '{message}'")
    logger.info("="*80)

    try:
        client = _get_promptql_client()

        response = client.continue_thread(
            thread_id=thread_id,
            message=message,
            system_instructions=system_instructions
        )

        if "error" in response:
            error_message = f"Error: {response['error']}\n{response.get('details', '')}"
            logger.error(f"ERROR RESPONSE: {error_message}")
            return error_message

        logger.info("PROCESSING PROMPTQL RESPONSE...")

        # Extract the answer from the thread response format
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

        # Look for artifact identifiers
        artifacts_found = []
        if interactions:
            for interaction in interactions:
                assistant_actions = interaction.get("assistant_actions", [])
                for action in assistant_actions:
                    artifact_identifiers = action.get("artifact_identifiers", [])
                    if artifact_identifiers:
                        artifacts_found.extend(artifact_identifiers)

        if artifacts_found:
            logger.info(f"ARTIFACT IDENTIFIERS FOUND: {len(artifacts_found)}")
            answer_text += f"\n\n**Artifacts Generated:** {', '.join(artifacts_found)}"

        logger.info("RESPONSE PROCESSED SUCCESSFULLY")
        return answer_text

    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        return f"Unexpected error: {str(e)}"

@mcp.tool(name="get_thread_status")
async def get_thread_status(thread_id: str) -> str:
    """
    Get the current status of a PromptQL thread.

    Args:
        thread_id: The ID of the thread to check

    Returns:
        Thread status information
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: get_thread_status")
    logger.info(f"Thread ID: {thread_id}")
    logger.info("="*80)

    try:
        client = _get_promptql_client()

        result = client.get_thread_status(thread_id)

        if "error" in result:
            error_message = f"Error: {result['error']}\n{result.get('details', '')}"
            logger.error(f"ERROR RESPONSE: {error_message}")
            return error_message

        status = result.get("status", "unknown")
        thread_data = result.get("thread_data", {})
        interactions_count = len(thread_data.get("interactions", []))

        status_message = f"Thread {thread_id}:\n"
        status_message += f"Status: {status}\n"
        status_message += f"Total interactions: {interactions_count}\n"

        if status == "processing":
            status_message += "The thread is currently processing. Check again in a few moments."
        elif status == "complete":
            status_message += "The thread has completed processing."

        logger.info(f"THREAD STATUS: {status}")
        return status_message

    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        return f"Unexpected error: {str(e)}"

@mcp.tool(name="cancel_thread")
async def cancel_thread(thread_id: str) -> str:
    """
    Cancel the processing of the latest interaction in a PromptQL thread.

    Args:
        thread_id: The ID of the thread to cancel

    Returns:
        Cancellation result message
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: cancel_thread")
    logger.info(f"Thread ID: {thread_id}")
    logger.info("="*80)

    try:
        client = _get_promptql_client()

        result = client.cancel_thread(thread_id)

        if "error" in result:
            error_message = f"Error: {result['error']}\n{result.get('details', '')}"
            logger.error(f"ERROR RESPONSE: {error_message}")
            return error_message

        message = result.get("message", "Thread cancelled")

        logger.info(f"THREAD CANCELLED: {thread_id}")
        return f"Thread {thread_id} cancellation result: {message}"

    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        return f"Unexpected error: {str(e)}"

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