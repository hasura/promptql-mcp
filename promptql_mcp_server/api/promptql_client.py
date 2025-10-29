# promptql_mcp_server/api/promptql_client.py

import requests
import json
import logging
import sys
import time
from typing import Dict

# Configure logging to output to stderr
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)

logger = logging.getLogger("promptql_client")

class PromptQLClient:
    """Client for interacting with the PromptQL Async Threads API."""

    def __init__(self, api_key: str, playground_url: str, auth_token: str, timezone: str = "America/Los_Angeles"):
        """Initialize the PromptQL API client."""
        self.api_key = api_key
        self.playground_url = playground_url.rstrip('/')  # Remove trailing slash if present
        self.auth_token = auth_token
        self.timezone = timezone
        
    def query(self, message: str, system_instructions: str = None) -> Dict:
        """Send a query to the PromptQL Async Threads API."""
        logger.info("="*80)
        logger.info(f"SENDING QUERY TO PROMPTQL: '{message}'")
        logger.info("="*80)

        # Debug API key - show first 8 chars and last 4 for verification
        api_key_debug = f"{self.api_key[:8]}...{self.api_key[-4:]}" if self.api_key else "None"
        logger.info(f"Using API Key: {api_key_debug}")
        logger.info(f"Using Playground URL: {self.playground_url}")
        logger.info(f"Using Auth Token: {self.auth_token[:8]}...{self.auth_token[-4:] if len(self.auth_token) > 8 else ''}")

        # Step 1: Start a new thread
        thread_id = self._start_thread(message, system_instructions)
        if isinstance(thread_id, dict) and "error" in thread_id:
            return thread_id

        # Step 2: Poll for thread completion
        return self._poll_thread_completion(thread_id)

    def _start_thread(self, message: str, system_instructions: str = None) -> str:
        """Start a new thread with the given message."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"api-key {self.api_key}"
        }

        # Build request body for new async API
        request_body = {
            "user_message": message,
            "ddn_headers": {
                "Auth-Token": self.auth_token
            },
            "timezone": self.timezone
        }

        # Add system instructions if provided
        if system_instructions:
            request_body["system_instructions"] = system_instructions

        # Print the request payload in a readable format
        logger.info("REQUEST PAYLOAD:")
        logger.info(json.dumps(request_body, indent=2))

        # Send request to start thread
        logger.info("STARTING NEW THREAD...")

        try:
            response = requests.post(
                f"{self.playground_url}/threads/v2/start",
                headers=headers,
                json=request_body,
                timeout=30
            )
        except Exception as e:
            logger.error(f"CONNECTION ERROR: {str(e)}")
            return {"error": f"Connection error: {str(e)}"}

        if response.status_code != 200:
            logger.error(f"ERROR: HTTP {response.status_code}")
            logger.error(f"Response: {response.text}")
            return {"error": f"API error: {response.status_code}", "details": response.text}

        try:
            result = response.json()
            thread_id = result.get("thread_id")
            if not thread_id:
                logger.error("No thread_id in response")
                return {"error": "No thread_id received from API"}

            logger.info(f"THREAD STARTED: {thread_id}")
            return thread_id
        except json.JSONDecodeError:
            logger.error("ERROR: Failed to parse JSON response")
            logger.error(f"Raw response: {response.text[:500]}...")
            return {"error": "Failed to parse thread start response"}

    def _poll_thread_completion(self, thread_id: str, max_wait_time: int = 120, poll_interval: int = 2) -> Dict:
        """Poll for thread completion and return the final result."""
        logger.info(f"POLLING THREAD {thread_id} FOR COMPLETION...")

        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            try:
                # Get thread state
                response = requests.get(
                    f"{self.playground_url}/threads/v2/{thread_id}",
                    headers={"Authorization": f"api-key {self.api_key}"},
                    timeout=30
                )

                if response.status_code != 200:
                    logger.error(f"ERROR polling thread: HTTP {response.status_code}")
                    logger.error(f"Response: {response.text}")
                    return {"error": f"Polling error: {response.status_code}", "details": response.text}

                # Parse the response - it might be server-sent events format
                thread_data = self._parse_thread_response(response.text)

                if thread_data and self._is_thread_complete(thread_data):
                    logger.info("THREAD COMPLETED")
                    return thread_data

                logger.info(f"Thread still processing, waiting {poll_interval}s...")
                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"ERROR polling thread: {str(e)}")
                return {"error": f"Polling error: {str(e)}"}

        logger.error(f"TIMEOUT: Thread did not complete within {max_wait_time} seconds")
        return {"error": f"Thread processing timeout after {max_wait_time} seconds"}

    def _parse_thread_response(self, response_text: str) -> Dict:
        """Parse the thread response, handling both JSON and server-sent events format."""
        try:
            # Try parsing as JSON first
            return json.loads(response_text)
        except json.JSONDecodeError:
            # Handle server-sent events format
            lines = response_text.strip().split('\n')
            thread_state = None

            for line in lines:
                if line.startswith('data: '):
                    try:
                        event_data = json.loads(line[6:])  # Remove 'data: ' prefix
                        if event_data.get("type") == "current_thread_state":
                            thread_state = event_data.get("thread_state", {})
                    except json.JSONDecodeError:
                        continue

            return thread_state or {}

    def _is_thread_complete(self, thread_data: Dict) -> bool:
        """Check if the thread processing is complete."""
        # Look for the latest interaction and check if it's complete
        interactions = thread_data.get("interactions", [])
        if not interactions:
            return False

        latest_interaction = interactions[-1]
        assistant_actions = latest_interaction.get("assistant_actions", [])

        # If there are assistant actions, check if the last one is complete
        if assistant_actions:
            last_action = assistant_actions[-1]
            # Check for completion indicators
            return (
                last_action.get("status") == "complete" or
                last_action.get("message") is not None or
                "llm_call_end_timestamp" in last_action
            )

        return False