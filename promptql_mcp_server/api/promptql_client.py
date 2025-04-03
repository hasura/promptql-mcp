# promptql_mcp_server/api/promptql_client.py

import requests
import json
import logging
import sys
from typing import Dict, List, Any, Optional, Tuple

# Configure logging to output to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger("promptql_client")

class PromptQLClient:
    """Client for interacting with the PromptQL Natural Language API."""
    
    def __init__(self, api_key: str, ddn_url: str, timezone: str = "America/Los_Angeles"):
        """Initialize the PromptQL API client."""
        self.api_key = api_key
        self.ddn_url = ddn_url
        self.timezone = timezone
        self.base_url = "https://api.promptql.pro.hasura.io"
        
    def query(self, 
              message: str, 
              artifacts: List[Dict] = None, 
              system_instructions: str = None, 
              llm_provider: str = "hasura", 
              stream: bool = False) -> Dict:
        """Send a query to the PromptQL API."""
        logger.info("="*80)
        logger.info(f"SENDING QUERY TO PROMPTQL: '{message}'")
        logger.info("="*80)
        
        # Debug API key - show first 8 chars and last 4 for verification
        api_key_debug = f"{self.api_key[:8]}...{self.api_key[-4:]}" if self.api_key else "None"
        logger.info(f"Using API Key: {api_key_debug}")
        logger.info(f"Using DDN URL: {self.ddn_url}")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Configure LLM provider
        llm_config = {"provider": llm_provider}
        
        # Build request body
        request_body = {
            "version": "v1",
            "llm": llm_config,
            "ddn": {
                "url": self.ddn_url,
                "headers": {}
            },
            "artifacts": artifacts or [],
            "timezone": self.timezone,
            "interactions": [
                {
                    "user_message": {
                        "text": message
                    },
                    "assistant_actions": []
                }
            ],
            "stream": stream
        }
        
        if system_instructions:
            request_body["system_instructions"] = system_instructions
        
        # Print the request payload in a readable format
        logger.info("REQUEST PAYLOAD:")
        logger.info(json.dumps(request_body, indent=2))
        
        # Send request
        logger.info("SENDING REQUEST TO PROMPTQL API...")
        
        try:
            response = requests.post(
                f"{self.base_url}/query",
                headers=headers,
                json=request_body,
                stream=stream,
                timeout=60  # Longer timeout for PromptQL to process
            )
        except Exception as e:
            logger.error(f"CONNECTION ERROR: {str(e)}")
            return {"error": f"Connection error: {str(e)}"}
        
        if response.status_code != 200:
            logger.error(f"ERROR: HTTP {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {"error": f"API error: {response.status_code}", "details": response.text}
        
        if not stream:
            try:
                result = response.json()
                logger.info("RECEIVED RESPONSE FROM PROMPTQL API")
                
                # Log only the beginning of large responses
                response_text = json.dumps(result, indent=2)
                if len(response_text) > 1000:
                    logger.info(f"RESPONSE PAYLOAD (truncated): {response_text[:1000]}...")
                else:
                    logger.info(f"RESPONSE PAYLOAD: {response_text}")
                
                # Check for artifacts
                if "modified_artifacts" in result:
                    artifacts = result["modified_artifacts"]
                    logger.info(f"FOUND {len(artifacts)} ARTIFACTS IN RESPONSE")
                    for idx, artifact in enumerate(artifacts):
                        logger.info(f"  Artifact {idx+1}: {artifact.get('title', 'Unnamed')} ({artifact.get('artifact_type', 'unknown')})")
                
                return result
            except json.JSONDecodeError:
                logger.error("ERROR: Failed to parse JSON response")
                logger.error(f"Raw response: {response.text[:500]}...")
                return {"error": "Failed to parse PromptQL response"}
        else:
            # Return the response object for streaming
            return response