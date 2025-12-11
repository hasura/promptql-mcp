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
    auth_mode = config.get_auth_mode()  # Defaults to "public" if not set

    logger.info(f"Loading config - API Key exists: {bool(api_key)}, Playground URL exists: {bool(playground_url)}, Auth Token exists: {bool(auth_token)}, Auth Mode: {auth_mode}")

    if not api_key or not playground_url or not auth_token:
        raise ValueError("PromptQL API key, playground URL, and auth token must be configured. Use the setup_config tool.")

    return PromptQLClient(api_key=api_key, playground_url=playground_url, auth_token=auth_token, auth_mode=auth_mode)



@mcp.tool(name="setup_config")
def setup_config(api_key: str, playground_url: str, auth_token: str, auth_mode: str = "public") -> dict:
    """
    Configure the PromptQL MCP server with API key, playground URL, and auth token.

    Args:
        api_key: PromptQL API key
        playground_url: PromptQL playground URL (e.g., https://promptql.<dataplane-name>.private-ddn.hasura.app/playground)
        auth_token: DDN Auth Token for accessing your data
        auth_mode: Authentication mode - "public" for Auth-Token or "private" for x-hasura-ddn-token (default: "public")

    Returns:
        Configuration result with success status and details
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: setup_config")
    # Log partial credentials for debugging
    masked_key = api_key[:5] + "..." + api_key[-5:] if api_key else "None"
    masked_token = auth_token[:8] + "..." + auth_token[-4:] if len(auth_token) > 12 else auth_token[:4] + "..."
    logger.info(f"API Key: '{masked_key}' (redacted middle)")
    logger.info(f"Playground URL: '{playground_url}'")
    logger.info(f"Auth Token: '{masked_token}' (redacted middle)")
    logger.info(f"Auth Mode: '{auth_mode}'")
    logger.info("="*80)

    # Validate auth_mode
    if auth_mode.lower() not in ["public", "private"]:
        return {
            "success": False,
            "error": f"Invalid auth_mode '{auth_mode}'. Must be 'public' or 'private'.",
            "configured_items": {}
        }

    config.set("api_key", api_key)
    config.set("playground_url", playground_url)
    config.set("auth_token", auth_token)
    config.set("auth_mode", auth_mode.lower())

    logger.info("CONFIGURATION SAVED SUCCESSFULLY")
    return {
        "success": True,
        "message": "Configuration saved successfully.",
        "configured_items": {
            "api_key": masked_key,
            "playground_url": playground_url,
            "auth_token": masked_token,
            "auth_mode": auth_mode.lower()
        }
    }

# Add a new tool to check configuration status
@mcp.tool(name="check_config")
def check_config() -> dict:
    """
    Check if the PromptQL MCP server is already configured with API key, playground URL, and auth token.

    Returns:
        Configuration status with detailed information about what's configured
    """
    logger.info("="*80)
    logger.info("TOOL CALL: check_config")
    logger.info("="*80)

    api_key = config.get("api_key")
    playground_url = config.get("playground_url")
    auth_token = config.get("auth_token")
    auth_mode = config.get_auth_mode()

    if api_key and playground_url and auth_token:
        masked_key = api_key[:5] + "..." + api_key[-5:] if api_key else "None"
        masked_token = auth_token[:8] + "..." + auth_token[-4:] if len(auth_token) > 12 else auth_token[:4] + "..."
        logger.info("CONFIGURATION CHECK: Already configured")
        return {
            "configured": True,
            "message": "PromptQL is fully configured",
            "configuration": {
                "api_key": masked_key,
                "playground_url": playground_url,
                "auth_token": masked_token,
                "auth_mode": auth_mode
            },
            "missing_items": []
        }
    else:
        missing = []
        if not api_key:
            missing.append("API Key")
        if not playground_url:
            missing.append("Playground URL")
        if not auth_token:
            missing.append("Auth Token")

        logger.info(f"CONFIGURATION CHECK: Missing {', '.join(missing)}")
        return {
            "configured": False,
            "message": f"PromptQL is not fully configured. Missing: {', '.join(missing)}",
            "configuration": {
                "api_key": api_key[:5] + "..." + api_key[-5:] if api_key else None,
                "playground_url": playground_url,
                "auth_token": auth_token[:8] + "..." + auth_token[-4:] if auth_token and len(auth_token) > 12 else auth_token[:4] + "..." if auth_token else None
            },
            "missing_items": missing
        }

@mcp.tool(name="start_thread")
async def start_thread(message: str, system_instructions: Optional[str] = None) -> dict:
    """
    Start a new PromptQL thread with a message and poll for completion.

    Args:
        message: The initial message to start the thread with
        system_instructions: Optional system instructions for the LLM

    Returns:
        Complete response from PromptQL with structured data including thread_id, interaction_id, answer, plans, code, and artifacts
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
            return {
                "success": False,
                "error": result['error'],
                "details": result.get('details', ''),
                "thread_id": None,
                "interaction_id": None
            }

        # Extract thread_id and interaction_id from the result
        thread_id = result.get("thread_id")
        interaction_id = result.get("interaction_id")

        if not thread_id:
            logger.error("No thread_id in response")
            return {
                "success": False,
                "error": "No thread_id received from PromptQL",
                "thread_id": None,
                "interaction_id": None
            }

        logger.info(f"THREAD COMPLETED: {thread_id}")

        # Extract structured data from the thread response
        answer_text = "No answer received from PromptQL."
        plans = []
        code_blocks = []
        code_outputs = []

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

                # Collect plans, code, and outputs from actions
                for action in assistant_actions:
                    # Collect plan if available
                    plan = action.get("plan")
                    if plan:
                        logger.info("EXECUTION PLAN FOUND")
                        plans.append(plan)

                    # Collect code if available
                    code = action.get("code")
                    if code:
                        logger.info("EXECUTED CODE FOUND")
                        code_blocks.append(code)

                    # Collect code output if available
                    code_output = action.get("code_output")
                    if code_output:
                        logger.info("CODE OUTPUT FOUND")
                        code_outputs.append(code_output)

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

        logger.info("FINAL RESPONSE PREPARED")
        return {
            "success": True,
            "thread_id": thread_id,
            "interaction_id": interaction_id,
            "answer": answer_text,
            "plans": plans,
            "code_blocks": code_blocks,
            "code_outputs": code_outputs,
            "artifacts": artifacts_found,
            "interactions_count": len(interactions),
            "raw_response": result
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        logger.error(error_trace)
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_trace": error_trace,
            "thread_id": None,
            "interaction_id": None
        }

@mcp.tool(name="start_thread_without_polling")
async def start_thread_without_polling(message: str, system_instructions: Optional[str] = None) -> dict:
    """
    Start a new PromptQL thread with a message without waiting for completion.

    Args:
        message: The initial message to start the thread with
        system_instructions: Optional system instructions for the LLM

    Returns:
        Thread ID and interaction ID for the started thread with status information
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
            return {
                "success": False,
                "error": result['error'],
                "details": result.get('details', ''),
                "thread_id": None,
                "interaction_id": None
            }

        # Extract thread_id and interaction_id from the result
        thread_id = result.get("thread_id")
        interaction_id = result.get("interaction_id")

        if not thread_id:
            logger.error("No thread_id in response")
            return {
                "success": False,
                "error": "No thread_id received from PromptQL",
                "thread_id": None,
                "interaction_id": None
            }

        logger.info(f"THREAD STARTED (NO POLLING): {thread_id}")

        logger.info("THREAD START RESPONSE PREPARED")
        return {
            "success": True,
            "thread_id": thread_id,
            "interaction_id": interaction_id,
            "message": "Thread started successfully. Use get_thread_status to check progress or continue_thread to add more messages.",
            "status": "started",
            "polling": False
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        logger.error(error_trace)
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "error_trace": error_trace,
            "thread_id": None,
            "interaction_id": None
        }

@mcp.tool(name="continue_thread")
async def continue_thread(thread_id: str, message: str, system_instructions: Optional[str] = None) -> dict:
    """
    Continue an existing PromptQL thread with a new message.

    Args:
        thread_id: The ID of the thread to continue
        message: The new message to add to the thread
        system_instructions: Optional system instructions for the LLM

    Returns:
        Structured response from PromptQL for the continued conversation with thread data, answer, plans, code, and artifacts
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
            return {
                "success": False,
                "error": response['error'],
                "details": response.get('details', ''),
                "thread_id": thread_id,
                "interaction_id": None
            }

        logger.info("PROCESSING PROMPTQL RESPONSE...")

        # Extract structured data from the thread response
        answer_text = "No answer received from PromptQL."
        plans = []
        code_blocks = []
        code_outputs = []

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

                # Collect plans, code, and outputs from actions
                for action in assistant_actions:
                    # Collect plan if available
                    plan = action.get("plan")
                    if plan:
                        logger.info("EXECUTION PLAN FOUND")
                        plans.append(plan)

                    # Collect code if available
                    code = action.get("code")
                    if code:
                        logger.info("EXECUTED CODE FOUND")
                        code_blocks.append(code)

                    # Collect code output if available
                    code_output = action.get("code_output")
                    if code_output:
                        logger.info("CODE OUTPUT FOUND")
                        code_outputs.append(code_output)

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

        # Extract interaction_id from the latest interaction
        interaction_id = None
        if interactions:
            interaction_id = interactions[-1].get("interaction_id")

        logger.info("RESPONSE PROCESSED SUCCESSFULLY")
        return {
            "success": True,
            "thread_id": thread_id,
            "interaction_id": interaction_id,
            "answer": answer_text,
            "plans": plans,
            "code_blocks": code_blocks,
            "code_outputs": code_outputs,
            "artifacts": artifacts_found,
            "interactions_count": len(interactions),
            "raw_response": response
        }

    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "thread_id": thread_id,
            "interaction_id": None
        }

@mcp.tool(name="get_thread_status")
async def get_thread_status(thread_id: str) -> dict:
    """
    Get the current status of a PromptQL thread with detailed information.
    Uses SSE (Server-Sent Events) streaming to get real-time thread state.

    Args:
        thread_id: The ID of the thread to check

    Returns:
        Comprehensive thread status as structured data including:
        - Thread status (processing/complete)
        - Thread metadata (title, version)
        - Total interactions count
        - Detailed breakdown of each interaction:
          * User messages with timestamps
          * Assistant actions with status
          * Messages, plans, code, and code output
          * Artifact identifiers
          * Timing information (start/end timestamps)
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
            return {
                "success": False,
                "error": result['error'],
                "details": result.get('details', ''),
                "thread_id": thread_id,
                "status": "error",
                "title": "",
                "version": "",
                "interactions_count": 0,
                "message": f"Error getting thread {thread_id} status",
                "interactions": []
            }

        status = result.get("status", "unknown")
        thread_data = result.get("thread_data", {})
        interactions = thread_data.get("interactions", [])
        interactions_count = len(interactions)

        # Extract additional metadata from SSE-enhanced thread data
        thread_title = thread_data.get("title", "")
        thread_version = thread_data.get("version", "")

        # Build structured response
        response_data = {
            "success": True,
            "thread_id": thread_id,
            "status": status,
            "interactions_count": interactions_count,
            "message": f"Thread {thread_id} is {status}",
            "title": thread_title,
            "version": thread_version,
            "interactions": []
        }

        # Add detailed information about interactions and assistant actions
        if interactions:
            for i, interaction in enumerate(interactions, 1):
                interaction_data = {
                    "interaction_number": i,
                    "interaction_id": interaction.get("interaction_id"),
                    "user_message": {},
                    "assistant_actions": []
                }

                # Process user message if available
                user_message_data = interaction.get("user_message", {})
                if user_message_data:
                    if isinstance(user_message_data, dict):
                        interaction_data["user_message"] = {
                            "message": user_message_data.get("message", ""),
                            "timestamp": user_message_data.get("timestamp", ""),
                            "timezone": user_message_data.get("timezone", ""),
                            "uploads": user_message_data.get("uploads", [])
                        }
                    else:
                        # Fallback for simple string format
                        interaction_data["user_message"] = {
                            "message": str(user_message_data),
                            "timestamp": "",
                            "timezone": "",
                            "uploads": []
                        }

                # Process assistant actions
                assistant_actions = interaction.get("assistant_actions", [])

                for j, action in enumerate(assistant_actions, 1):
                    action_data = {
                        "action_number": j,
                        "action_id": action.get("action_id"),
                        "status": action.get("status", "unknown"),
                        "message": action.get("message", ""),
                        "plan": action.get("plan", ""),
                        "code": {},
                        "code_output": action.get("code_output", ""),
                        "artifacts": action.get("artifact_identifiers", []),
                        "timing": {
                            "created_timestamp": action.get("created_timestamp", ""),
                            "response_start_timestamp": action.get("response_start_timestamp", ""),
                            "action_end_timestamp": action.get("action_end_timestamp", ""),
                            "llm_call_start_timestamp": action.get("llm_call_start_timestamp", ""),
                            "llm_call_end_timestamp": action.get("llm_call_end_timestamp", "")
                        }
                    }

                    # Process code data if available
                    code_data = action.get("code", {})
                    if code_data:
                        if isinstance(code_data, dict):
                            action_data["code"] = {
                                "code_block_id": code_data.get("code_block_id", ""),
                                "code": code_data.get("code", ""),
                                "query_plan": code_data.get("query_plan", ""),
                                "execution_start_timestamp": code_data.get("execution_start_timestamp"),
                                "execution_end_timestamp": code_data.get("execution_end_timestamp"),
                                "output": code_data.get("output"),
                                "error": code_data.get("error"),
                                "sql_statements": code_data.get("sql_statements", [])
                            }
                        else:
                            # Fallback for simple string format
                            action_data["code"] = {"code": str(code_data)}

                    interaction_data["assistant_actions"].append(action_data)

                response_data["interactions"].append(interaction_data)

        # Add raw thread data for advanced use cases
        response_data["raw_thread_data"] = thread_data

        logger.info(f"THREAD STATUS: {status}")
        return response_data

    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "thread_id": thread_id,
            "status": "error",
            "title": "",
            "version": "",
            "interactions_count": 0,
            "message": f"Unexpected error getting thread {thread_id} status",
            "interactions": []
        }

@mcp.tool(name="cancel_thread")
async def cancel_thread(thread_id: str) -> dict:
    """
    Cancel the processing of the latest interaction in a PromptQL thread.

    Args:
        thread_id: The ID of the thread to cancel

    Returns:
        Cancellation result with success status and details
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
            return {
                "success": False,
                "error": result['error'],
                "details": result.get('details', ''),
                "thread_id": thread_id
            }

        message = result.get("message", "Thread cancelled")

        logger.info(f"THREAD CANCELLED: {thread_id}")
        return {
            "success": True,
            "thread_id": thread_id,
            "message": message,
            "action": "cancelled",
            "raw_response": result
        }

    except Exception as e:
        logger.error(f"UNEXPECTED ERROR: {str(e)}")
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
            "thread_id": thread_id
        }

@mcp.tool(name="get_artifact")
def get_artifact(thread_id: str, artifact_id: str) -> dict:
    """
    Get artifact data from a specific thread.

    Args:
        thread_id: The ID of the thread containing the artifact
        artifact_id: The ID of the artifact to retrieve

    Returns:
        Dictionary containing artifact data, metadata, and retrieval status
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: get_artifact")
    logger.info(f"Thread ID: {thread_id}")
    logger.info(f"Artifact ID: {artifact_id}")
    logger.info("="*80)

    try:
        client = _get_promptql_client()
        response_data = client.get_artifact(thread_id, artifact_id)

        if "error" in response_data:
            logger.error(f"ERROR getting artifact: {response_data['error']}")
            return {
                "success": False,
                "error": response_data["error"],
                "details": response_data.get("details", ""),
                "thread_id": thread_id,
                "artifact_id": artifact_id
            }

        logger.info(f"ARTIFACT RETRIEVED: {artifact_id}")
        logger.info(f"Content Type: {response_data.get('content_type', 'unknown')}")
        logger.info(f"Size: {response_data.get('size', 0)} bytes")

        return {
            "success": True,
            "thread_id": thread_id,
            "artifact_id": artifact_id,
            "content_type": response_data.get("content_type"),
            "size": response_data.get("size"),
            "data": response_data.get("data"),
            "message": f"Artifact {artifact_id} retrieved successfully from thread {thread_id}",
            "raw_response": response_data
        }
    except Exception as e:
        logger.error(f"ERROR in get_artifact tool: {str(e)}")
        return {
            "success": False,
            "error": f"Get artifact error: {str(e)}",
            "thread_id": thread_id,
            "artifact_id": artifact_id
        }

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