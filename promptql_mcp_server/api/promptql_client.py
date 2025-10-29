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
        

    def start_thread(self, message: str, system_instructions: str = None) -> Dict:
        """Start a new thread and poll for completion, returning complete response."""
        logger.info("="*80)
        logger.info(f"STARTING NEW THREAD: '{message}'")
        logger.info("="*80)

        start_result = self._start_thread(message, system_instructions)
        if isinstance(start_result, dict) and "error" in start_result:
            return start_result

        thread_id = start_result.get("thread_id")
        interaction_id = start_result.get("interaction_id")
        if not thread_id:
            return {"error": "No thread_id received from start_thread"}

        # Step 2: Poll for thread completion
        completion_result = self._poll_thread_completion(thread_id)

        # Add thread_id and interaction_id to the completion result
        if isinstance(completion_result, dict) and "error" not in completion_result:
            completion_result["thread_id"] = thread_id
            completion_result["interaction_id"] = interaction_id

        return completion_result

    def start_thread_without_polling(self, message: str, system_instructions: str = None) -> Dict:
        """Start a new thread without waiting for completion. Returns thread_id and interaction_id immediately."""
        logger.info("="*80)
        logger.info(f"STARTING NEW THREAD (NO POLLING): '{message}'")
        logger.info("="*80)

        return self._start_thread(message, system_instructions)

    def continue_thread(self, thread_id: str, message: str, system_instructions: str = None) -> Dict:
        """Continue an existing thread with a new message."""
        logger.info("="*80)
        logger.info(f"CONTINUING THREAD {thread_id}: '{message}'")
        logger.info("="*80)

        # Step 1: Add new interaction to thread
        continue_result = self._continue_thread(thread_id, message, system_instructions)
        if isinstance(continue_result, dict) and "error" in continue_result:
            return continue_result

        # Step 2: Poll for thread completion
        return self._poll_thread_completion(thread_id)

    def get_thread_status(self, thread_id: str) -> Dict:
        """Get the current status of a thread without polling."""
        logger.info(f"GETTING THREAD STATUS: {thread_id}")

        try:
            response = requests.get(
                f"{self.playground_url}/threads/v2/{thread_id}",
                headers={"Authorization": f"api-key {self.api_key}"},
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"ERROR getting thread status: HTTP {response.status_code}")
                return {"error": f"Status error: {response.status_code}", "details": response.text}

            # Parse the response
            thread_data = self._parse_thread_response(response.text)

            if thread_data:
                is_complete = self._is_thread_complete(thread_data)
                return {
                    "thread_id": thread_id,
                    "status": "complete" if is_complete else "processing",
                    "thread_data": thread_data
                }
            else:
                return {"error": "Failed to parse thread status"}

        except Exception as e:
            logger.error(f"ERROR getting thread status: {str(e)}")
            return {"error": f"Status error: {str(e)}"}

    def cancel_thread(self, thread_id: str) -> Dict:
        """Cancel the processing of the latest interaction in a thread."""
        logger.info(f"CANCELLING THREAD: {thread_id}")

        try:
            response = requests.post(
                f"{self.playground_url}/threads/v2/{thread_id}/cancel",
                headers={"Authorization": f"api-key {self.api_key}"},
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"THREAD CANCELLED: {thread_id}")
                return {
                    "thread_id": thread_id,
                    "status": "cancelled",
                    "message": "Thread processing cancelled successfully"
                }
            elif response.status_code == 400:
                # Thread is not currently processing
                logger.warning(f"Cannot cancel thread {thread_id}: not currently processing")
                return {
                    "error": "Cannot cancel thread",
                    "details": "Thread is not currently processing an interaction"
                }
            else:
                logger.error(f"ERROR cancelling thread: HTTP {response.status_code}")
                return {"error": f"Cancel error: {response.status_code}", "details": response.text}

        except Exception as e:
            logger.error(f"ERROR cancelling thread: {str(e)}")
            return {"error": f"Cancel error: {str(e)}"}

    def get_artifact(self, thread_id: str, artifact_id: str) -> Dict:
        """Get artifact data from a thread."""
        logger.info(f"GETTING ARTIFACT: {artifact_id} from thread {thread_id}")

        try:
            response = requests.get(
                f"{self.playground_url}/threads/v2/{thread_id}/artifacts/{artifact_id}/data",
                headers={"Authorization": f"api-key {self.api_key}"},
                timeout=30
            )

            if response.status_code == 200:
                logger.info(f"ARTIFACT RETRIEVED: {artifact_id}")

                # Try to parse as JSON first
                try:
                    artifact_data = response.json()
                    return {
                        "thread_id": thread_id,
                        "artifact_id": artifact_id,
                        "content_type": response.headers.get("content-type", "application/json"),
                        "data": artifact_data,
                        "size": len(response.content)
                    }
                except json.JSONDecodeError:
                    # If not JSON, return as text
                    return {
                        "thread_id": thread_id,
                        "artifact_id": artifact_id,
                        "content_type": response.headers.get("content-type", "text/plain"),
                        "data": response.text,
                        "size": len(response.content)
                    }
            elif response.status_code == 404:
                logger.warning(f"Artifact {artifact_id} not found in thread {thread_id}")
                return {
                    "error": "Artifact not found",
                    "details": f"Artifact {artifact_id} not found in thread {thread_id}"
                }
            else:
                logger.error(f"ERROR getting artifact: HTTP {response.status_code}")
                return {"error": f"Artifact error: {response.status_code}", "details": response.text}

        except Exception as e:
            logger.error(f"ERROR getting artifact: {str(e)}")
            return {"error": f"Artifact error: {str(e)}"}

    def _start_thread(self, message: str, system_instructions: str = None) -> Dict:
        """Start a new thread with the given message. Returns thread_id and interaction_id."""
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
            interaction_id = result.get("interaction_id")

            if not thread_id:
                logger.error("No thread_id in response")
                return {"error": "No thread_id received from API"}

            logger.info(f"THREAD STARTED: {thread_id}, INTERACTION: {interaction_id}")
            return result  # Returns {"thread_id": "...", "interaction_id": "..."}
        except json.JSONDecodeError:
            logger.error("ERROR: Failed to parse JSON response")
            logger.error(f"Raw response: {response.text[:500]}...")
            return {"error": "Failed to parse thread start response"}

    def _poll_thread_completion(self, thread_id: str, max_wait_time: int = 120, poll_interval: int = 2) -> Dict:
        """Poll for thread completion and return the final result."""
        logger.info(f"POLLING THREAD {thread_id} FOR COMPLETION...")

        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            # Use get_thread_status to check thread status
            status_result = self.get_thread_status(thread_id)

            # Handle errors from get_thread_status
            if "error" in status_result:
                logger.error(f"ERROR polling thread: {status_result.get('error')}")
                return status_result

            # Check if thread is complete
            if status_result.get("status") == "complete":
                logger.info("THREAD COMPLETED")
                return status_result.get("thread_data", {})

            logger.info(f"Thread still processing, waiting {poll_interval}s...")
            time.sleep(poll_interval)

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

    def _continue_thread(self, thread_id: str, message: str, system_instructions: str = None) -> Dict:
        """Add a new interaction to an existing thread. Returns thread_id and interaction_id."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"api-key {self.api_key}"
        }

        # Build request body for continue API
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
        logger.info("CONTINUE REQUEST PAYLOAD:")
        logger.info(json.dumps(request_body, indent=2))

        # Send request to continue thread
        logger.info(f"CONTINUING THREAD {thread_id}...")

        try:
            response = requests.post(
                f"{self.playground_url}/threads/v2/{thread_id}/continue",
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
            returned_thread_id = result.get("thread_id")
            interaction_id = result.get("interaction_id")

            if returned_thread_id != thread_id:
                logger.warning(f"Thread ID mismatch: expected {thread_id}, got {returned_thread_id}")

            logger.info(f"THREAD CONTINUED: {thread_id}, INTERACTION: {interaction_id}")
            return result  # Returns {"thread_id": "...", "interaction_id": "..."}
        except json.JSONDecodeError:
            logger.error("ERROR: Failed to parse JSON response")
            logger.error(f"Raw response: {response.text[:500]}...")
            return {"error": "Failed to parse thread continue response"}