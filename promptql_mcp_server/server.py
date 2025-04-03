# promptql_mcp_server/server.py

from mcp.server.fastmcp import FastMCP, Image, Context
from typing import Dict, List, Any, Optional, Union
import json
import base64
import logging
import sys

from promptql_mcp_server.api.promptql_client import PromptQLClient
from promptql_mcp_server.config import ConfigManager

# Ensure logger is configured to output to stderr
logger = logging.getLogger("promptql_server")

# Initialize configuration
config = ConfigManager()

# Create an MCP server
mcp = FastMCP("PromptQL", 
               description="Access your data using natural language queries powered by PromptQL")

def _get_promptql_client() -> PromptQLClient:
    """Get a configured PromptQL client."""
    api_key = config.get("api_key")
    ddn_url = config.get("ddn_url")
    
    logger.info(f"Loading config - API Key exists: {bool(api_key)}, DDN URL exists: {bool(ddn_url)}")
    
    if not api_key or not ddn_url:
        raise ValueError("PromptQL API key and DDN URL must be configured. Use the setup_config tool.")
    
    return PromptQLClient(api_key=api_key, ddn_url=ddn_url)

@mcp.tool(name="ask_question")
async def ask_question(question: str, system_instructions: Optional[str] = None, ctx: Optional[Context] = None) -> str:
    """
    Ask a natural language question to PromptQL.
    
    Args:
        question: The natural language query to ask
        system_instructions: Optional system instructions for the LLM
        ctx: MCP context (automatically provided)
        
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
            system_instructions=system_instructions,
            stream=False
        )
        
        if "error" in response:
            error_message = f"Error: {response['error']}\n{response.get('details', '')}"
            logger.error(f"ERROR RESPONSE: {error_message}")
            return error_message
        
        logger.info("PROCESSING PROMPTQL RESPONSE...")
        
        # Extract the answer from the response - using last action message by default
        answer_text = "No answer received from PromptQL."
        
        if "assistant_actions" in response and response["assistant_actions"]:
            # Get the last assistant action with a message (most likely the final response)
            for action in reversed(response["assistant_actions"]):
                if action.get("message"):
                    answer_text = action.get("message", "")
                    break
            
            # Add plan and code from the first action (usually contains execution details)
            first_action = response["assistant_actions"][0]
            
            # Add plan if available
            plan = first_action.get("plan")
            if plan:
                logger.info("EXECUTION PLAN FOUND")
                if "**Execution Plan:**" not in answer_text:
                    answer_text += f"\n\n**Execution Plan:**\n{plan}"
            
            # Add code if available
            code = first_action.get("code")
            if code:
                logger.info("EXECUTED CODE FOUND")
                if "**Executed Code:**" not in answer_text:
                    answer_text += f"\n\n**Executed Code:**\n{code}"
                    
            # Add code output if available
            code_output = first_action.get("code_output")
            if code_output:
                logger.info("CODE OUTPUT FOUND")
                if "**Code Output:**" not in answer_text:
                    answer_text += f"\n\n**Code Output:**\n{code_output}"
        
        # Process artifacts if available
        if "modified_artifacts" in response and response["modified_artifacts"]:
            artifacts = response["modified_artifacts"]
            logger.info(f"ARTIFACTS FOUND: {len(artifacts)}")
            
            for artifact in artifacts:
                artifact_id = artifact.get("identifier")
                artifact_title = artifact.get("title", "Unnamed Artifact")
                artifact_type = artifact.get("artifact_type")
                artifact_data = artifact.get("data")
                
                logger.info(f"Processing artifact: {artifact_title} (Type: {artifact_type}, ID: {artifact_id})")
                
                # Process based on artifact type
                if artifact_type == "table" and isinstance(artifact_data, list):
                    logger.info("Processing table artifact")
                    
                    # Create a nicely formatted markdown table
                    try:
                        # Make sure we have data and it's a list of dicts
                        if artifact_data and isinstance(artifact_data[0], dict):
                            columns = list(artifact_data[0].keys())
                            
                            table_md = f"\n\n**{artifact_title}**\n\n"
                            table_md += "| " + " | ".join(columns) + " |\n"
                            table_md += "| " + " | ".join(["---"] * len(columns)) + " |\n"
                            
                            for row in artifact_data:
                                table_md += "| " + " | ".join([str(row.get(col, "")) for col in columns]) + " |\n"
                            
                            # Don't duplicate tables - check if it's already in answer
                            if f"**{artifact_title}**" not in answer_text:
                                answer_text += table_md
                    except Exception as e:
                        logger.error(f"Error formatting table: {e}")
                
                elif artifact_type == "image" and artifact_data:
                    logger.info("Processing image artifact")
                    # For images, try to create an MCP image if context available
                    try:
                        if ctx:
                            # Images might be base64 encoded
                            if isinstance(artifact_data, str):
                                # Try to decode if it's base64
                                try:
                                    image_data = base64.b64decode(artifact_data)
                                except:
                                    # If not base64, use as is
                                    image_data = artifact_data.encode('utf-8')
                            else:
                                # If it's bytes already, use as is
                                image_data = artifact_data
                                
                            # Create image resource
                            await ctx.create_image(image_data, title=artifact_title)
                            answer_text += f"\n\n*Image '{artifact_title}' has been attached.*"
                    except Exception as e:
                        logger.error(f"Error processing image: {e}")
                        
                elif artifact_type == "text" and artifact_data:
                    logger.info("Processing text artifact")
                    # Don't duplicate text if it's already in the answer
                    if artifact_data not in answer_text:
                        answer_text += f"\n\n**{artifact_title}**:\n{artifact_data}"
        
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
def setup_config(api_key: str, ddn_url: str) -> str:
    """
    Configure the PromptQL MCP server with API key and DDN URL.
    
    Args:
        api_key: PromptQL API key
        ddn_url: Project SQL endpoint URL
        
    Returns:
        Success message
    """
    logger.info("="*80)
    logger.info(f"TOOL CALL: setup_config")
    # Log partial API key for debugging
    masked_key = api_key[:5] + "..." + api_key[-5:] if api_key else "None"
    logger.info(f"API Key: '{masked_key}' (redacted middle)")
    logger.info(f"DDN URL: '{ddn_url}'")
    logger.info("="*80)
    
    config.set("api_key", api_key)
    config.set("ddn_url", ddn_url)
    
    logger.info("CONFIGURATION SAVED SUCCESSFULLY")
    return "Configuration saved successfully."

# Add a new tool to check configuration status
@mcp.tool(name="check_config")
def check_config() -> str:
    """
    Check if the PromptQL MCP server is already configured with API key and DDN URL.
    
    Returns:
        Configuration status message
    """
    logger.info("="*80)
    logger.info("TOOL CALL: check_config")
    logger.info("="*80)
    
    api_key = config.get("api_key")
    ddn_url = config.get("ddn_url")
    
    if api_key and ddn_url:
        masked_key = api_key[:5] + "..." + api_key[-5:] if api_key else "None"
        status = f"PromptQL is configured with:\nAPI Key: {masked_key}\nDDN URL: {ddn_url}"
        logger.info("CONFIGURATION CHECK: Already configured")
        return status
    else:
        missing = []
        if not api_key:
            missing.append("API Key")
        if not ddn_url:
            missing.append("DDN URL")
        
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