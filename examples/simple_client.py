import asyncio
import json
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

                    # Parse the dictionary response
                    if hasattr(result, 'content') and result.content and result.content[0].text:
                        try:
                            config_data = json.loads(result.content[0].text)
                            if config_data.get("success"):
                                print(f"✅ Configuration successful: {config_data.get('message')}")
                                print(f"📋 Configured items: {list(config_data.get('configured_items', {}).keys())}")
                            else:
                                print(f"❌ Configuration failed: {config_data.get('error', 'Unknown error')}")
                        except json.JSONDecodeError:
                            print(f"Configuration result: {result}")
                    else:
                        print(f"Configuration result: {result}")
            
                # Choose interaction mode
                print("\nChoose interaction mode:")
                print("1. Multi-turn conversation (thread-based)")
                print("2. Thread management demo")
                print("3. Thread cancellation demo")
                print("4. Start thread without polling demo")
                print("5. Artifact retrieval demo")
                mode = input("Enter choice (1, 2, 3, 4, or 5): ").strip()

                if mode == "1":
                    await multi_turn_conversation(client)
                elif mode == "2":
                    await thread_management_demo(client)
                elif mode == "3":
                    await thread_cancellation_demo(client)
                elif mode == "4":
                    await start_thread_without_polling_demo(client)
                elif mode == "5":
                    await artifact_demo(client)
                else:
                    print("Invalid choice. Using multi-turn conversation mode.")
                    await multi_turn_conversation(client)

    except Exception as e:
        print(f"Error occurred: {e}")
        print(traceback.format_exc())



async def multi_turn_conversation(client):
    """Demonstrate multi-turn conversation using thread management."""
    print("\n" + "="*80)
    print("MULTI-TURN CONVERSATION MODE")
    print("="*80)
    print("This mode allows you to have a conversation with PromptQL where")
    print("each question builds on the previous context.")
    print("Type 'quit' to exit, 'status' to check thread status, 'cancel' to cancel processing.")
    print("="*80)

    thread_id = None
    conversation_count = 0

    while True:
        if thread_id is None:
            # Start a new thread
            question = input(f"\n[Question {conversation_count + 1}] Enter your first question: ").strip()
            if not question:
                print("No question provided.")
                continue

            if question.lower() == 'quit':
                break

            print(f"\n🚀 Starting new thread...")
            result = await client.call_tool("start_thread", {"message": question})
            print(f"Result: {result}")

            # Parse the dictionary response
            if hasattr(result, 'content') and result.content and result.content[0].text:
                try:
                    result_data = json.loads(result.content[0].text)

                    if result_data.get("success"):
                        thread_id = result_data.get("thread_id")
                        conversation_count += 1
                        print(f"✅ Thread started with ID: {thread_id}")

                        # Display the structured response
                        print(f"\n📝 Answer:")
                        print(result_data.get("answer", "No answer available"))

                        # Show additional info if available
                        if result_data.get("plans"):
                            print(f"\n📋 Plans: {len(result_data['plans'])} found")
                        if result_data.get("code_blocks"):
                            print(f"\n� Code blocks: {len(result_data['code_blocks'])} found")
                        if result_data.get("artifacts"):
                            print(f"\n📎 Artifacts: {result_data['artifacts']}")

                        print(f"\n📊 Interactions: {result_data.get('interactions_count', 0)}")
                    else:
                        print(f"❌ Failed to start thread: {result_data.get('error', 'Unknown error')}")
                        continue
                except json.JSONDecodeError:
                    print("❌ Failed to parse response as JSON")
                    continue
            else:
                print("❌ Failed to start thread")
                continue
        else:
            # Continue the existing thread
            question = input(f"\n[Question {conversation_count + 1}] Continue conversation (or 'quit'/'status'): ").strip()
            if not question:
                continue

            if question.lower() == 'quit':
                break
            elif question.lower() == 'status':
                status_result = await client.call_tool("get_thread_status", {"thread_id": thread_id})

                # Parse status response
                if hasattr(status_result, 'content') and status_result.content and status_result.content[0].text:
                    try:
                        status_data = json.loads(status_result.content[0].text)
                        print(f"📊 Thread Status:")
                        print(f"   Status: {status_data.get('status', 'Unknown')}")
                        print(f"   Interactions: {status_data.get('interactions_count', 0)}")
                        print(f"   Message: {status_data.get('message', 'No message')}")
                    except json.JSONDecodeError:
                        print(f"📊 Thread status: {status_result}")
                else:
                    print(f"📊 Thread status: {status_result}")
                continue

            print(f"\n💬 Continuing thread {thread_id}...")
            result = await client.call_tool("continue_thread", {
                "thread_id": thread_id,
                "message": question
            })
            conversation_count += 1

            # Parse continue_thread response
            if hasattr(result, 'content') and result.content and result.content[0].text:
                try:
                    continue_data = json.loads(result.content[0].text)
                    if continue_data.get("success"):
                        print(f"\n📝 Answer:")
                        print(continue_data.get("answer", "No answer available"))

                        # Show additional info if available
                        if continue_data.get("plans"):
                            print(f"\n📋 Plans: {len(continue_data['plans'])} found")
                        if continue_data.get("code_blocks"):
                            print(f"\n� Code blocks: {len(continue_data['code_blocks'])} found")
                        if continue_data.get("artifacts"):
                            print(f"\n📎 Artifacts: {continue_data['artifacts']}")

                        print(f"\n📊 Total interactions: {continue_data.get('interactions_count', 0)}")
                    else:
                        print(f"❌ Error continuing thread: {continue_data.get('error', 'Unknown error')}")
                except json.JSONDecodeError:
                    print(f"\n📝 Response:")
                    print(result)
            else:
                print(f"\n�📝 Response:")
                print(result)

    if thread_id:
        print(f"\n🏁 Conversation ended. Final thread ID: {thread_id}")
        print(f"📈 Total questions asked: {conversation_count}")

        # Get final status
        final_status = await client.call_tool("get_thread_status", {"thread_id": thread_id})

        # Parse final status response
        if hasattr(final_status, 'content') and final_status.content and final_status.content[0].text:
            try:
                final_data = json.loads(final_status.content[0].text)
                print(f"📊 Final Thread Status:")
                print(f"   Status: {final_data.get('status', 'Unknown')}")
                print(f"   Total Interactions: {final_data.get('interactions_count', 0)}")
                print(f"   Message: {final_data.get('message', 'No message')}")
            except json.JSONDecodeError:
                print(f"📊 Final thread status: {final_status}")
        else:
            print(f"📊 Final thread status: {final_status}")

async def thread_management_demo(client):
    """Demonstrate thread management capabilities using continue_thread."""
    print("\n" + "="*80)
    print("THREAD MANAGEMENT DEMO")
    print("="*80)
    print("This demo shows how to use continue_thread to build conversations.")
    print("We'll start one thread and continue it with multiple related questions.")
    print("="*80)

    # Start the initial thread
    initial_question = "What tables are available in my database?"
    print(f"\n🚀 Starting thread with: {initial_question}")

    result = await client.call_tool("start_thread", {"message": initial_question})
    print(f"Start result: {result}")

    # Parse the dictionary response
    if hasattr(result, 'content') and result.content and result.content[0].text:
        try:
            result_data = json.loads(result.content[0].text)

            if result_data.get("success"):
                thread_id = result_data.get("thread_id")
                print(f"✅ Thread started with ID: {thread_id}")

                # Display the structured initial response
                print(f"\n📝 Initial Answer:")
                print(result_data.get("answer", "No answer available"))

                # Show additional info if available
                if result_data.get("plans"):
                    print(f"\n📋 Plans: {len(result_data['plans'])} found")
                if result_data.get("code_blocks"):
                    print(f"\n💻 Code blocks: {len(result_data['code_blocks'])} found")
                if result_data.get("artifacts"):
                    print(f"\n� Artifacts: {result_data['artifacts']}")
            else:
                print(f"❌ Failed to start thread: {result_data.get('error', 'Unknown error')}")
                return
        except json.JSONDecodeError:
            print("❌ Failed to parse response as JSON")
            return
    else:
        print("❌ Failed to start thread")
        return

    # Continue with related questions using the same thread
    follow_up_questions = [
            "Tell me more about the largest table you found",
            "Show me the schema of that table",
            "How many records are in that table?",
            "Can you show me a sample of data from it?"
        ]

    print(f"\n🔄 Continuing thread with {len(follow_up_questions)} follow-up questions...")

    for i, question in enumerate(follow_up_questions, 1):
        print(f"\n--- Follow-up {i} ---")
        print(f"Question: {question}")

        # Check status before asking the follow-up question
        print("📊 Checking thread status before continuing...")
        pre_status = await client.call_tool("get_thread_status", {"thread_id": thread_id})

        # Parse pre-status response
        if hasattr(pre_status, 'content') and pre_status.content and pre_status.content[0].text:
            try:
                pre_data = json.loads(pre_status.content[0].text)
                print(f"Pre-continue status: {pre_data.get('status', 'Unknown')} ({pre_data.get('interactions_count', 0)} interactions)")
            except json.JSONDecodeError:
                print(f"Pre-continue status: {pre_status}")
        else:
            print(f"Pre-continue status: {pre_status}")

        # Use continue_thread to maintain context
        continue_result = await client.call_tool("continue_thread", {
            "thread_id": thread_id,
            "message": question
        })

        # Parse continue result
        if hasattr(continue_result, 'content') and continue_result.content and continue_result.content[0].text:
            try:
                continue_data = json.loads(continue_result.content[0].text)
                if continue_data.get("success"):
                    print(f"✅ Continue successful - Answer: {continue_data.get('answer', 'No answer')[:100]}...")
                else:
                    print(f"❌ Continue failed: {continue_data.get('error', 'Unknown error')}")
            except json.JSONDecodeError:
                print(f"Continue result: {continue_result}")
        else:
            print(f"Continue result: {continue_result}")

        # Check status after each continuation
        status_result = await client.call_tool("get_thread_status", {"thread_id": thread_id})

        # Parse post-status response
        if hasattr(status_result, 'content') and status_result.content and status_result.content[0].text:
            try:
                post_data = json.loads(status_result.content[0].text)
                print(f"📊 Post-continue status: {post_data.get('status', 'Unknown')} ({post_data.get('interactions_count', 0)} interactions)")
            except json.JSONDecodeError:
                print(f"📊 Post-continue status: {status_result}")
        else:
            print(f"📊 Post-continue status: {status_result}")

        # Small delay between questions
        await asyncio.sleep(2)

    print(f"\n🏁 Demo completed. Used continue_thread {len(follow_up_questions)} times on thread {thread_id[:8]}...")

    print("\nKey benefits of continue_thread:")
    print("- Maintains conversation context across questions")
    print("- More efficient than creating new threads")
    print("- Allows for natural follow-up questions")
    print("- Thread remembers previous answers and context")

async def thread_cancellation_demo(client):
    """Demonstrate thread cancellation functionality."""
    print("\n" + "="*80)
    print("THREAD CANCELLATION DEMO")
    print("="*80)
    print("This demo shows how to cancel thread processing while it's running.")
    print("We'll start a thread without polling and then cancel it during processing.")
    print("="*80)

    # Start a thread with a complex question that will take time to process
    complex_question = "Analyze all tables in my database, show their relationships, and provide detailed statistics for each table including row counts, column types, and data quality metrics."

    print(f"\n🚀 Starting thread without polling...")
    print(f"Question: {complex_question}")

    result = await client.call_tool("start_thread_without_polling", {"message": complex_question})
    print(f"Start result: {result}")

    # Parse the dictionary response
    if hasattr(result, 'content') and result.content and result.content[0].text:
        try:
            result_data = json.loads(result.content[0].text)

            if result_data.get("success"):
                thread_id = result_data.get("thread_id")
                print(f"✅ Thread started with ID: {thread_id}")

                # Display the immediate response (should just be thread info)
                print(f"\n📝 Immediate Response:")
                print(f"Thread ID: {thread_id}")
                print(f"Interaction ID: {result_data.get('interaction_id')}")
                print(f"Status: {result_data.get('status')}")
                print(f"Message: {result_data.get('message')}")
            else:
                print(f"❌ Failed to start thread: {result_data.get('error', 'Unknown error')}")
                return
        except json.JSONDecodeError:
            print("❌ Failed to parse response as JSON")
            return
    else:
        print("❌ Failed to start thread")
        return

    # Give the thread a moment to start processing
    print("\n⏳ Waiting 3 seconds for processing to begin...")
    await asyncio.sleep(3)

    # Check status (should be processing)
    print("\n📊 Checking thread status...")
    status_result = await client.call_tool("get_thread_status", {"thread_id": thread_id})

    # Parse status response
    if hasattr(status_result, 'content') and status_result.content and status_result.content[0].text:
        try:
            status_data = json.loads(status_result.content[0].text)
            print(f"Status: {status_data.get('status', 'Unknown')} ({status_data.get('interactions_count', 0)} interactions)")
        except json.JSONDecodeError:
            print(f"Status: {status_result}")
    else:
        print(f"Status: {status_result}")

    # Attempt to cancel while processing
    print(f"\n🛑 Attempting to cancel thread {thread_id} while processing...")
    cancel_result = await client.call_tool("cancel_thread", {"thread_id": thread_id})

    # Parse cancel result
    if hasattr(cancel_result, 'content') and cancel_result.content and cancel_result.content[0].text:
        try:
            cancel_data = json.loads(cancel_result.content[0].text)
            if cancel_data.get("success"):
                print(f"✅ Cancel successful: {cancel_data.get('message')}")
            else:
                print(f"❌ Cancel failed: {cancel_data.get('error', 'Unknown error')}")
        except json.JSONDecodeError:
            print(f"Cancel result: {cancel_result}")
    else:
        print(f"Cancel result: {cancel_result}")

    # Check status after cancellation
    print("\n📊 Checking thread status after cancellation...")
    final_status = await client.call_tool("get_thread_status", {"thread_id": thread_id})

    # Parse final status response
    if hasattr(final_status, 'content') and final_status.content and final_status.content[0].text:
        try:
            final_data = json.loads(final_status.content[0].text)
            print(f"Final status: {final_data.get('status', 'Unknown')} ({final_data.get('interactions_count', 0)} interactions)")
        except json.JSONDecodeError:
            print(f"Final status: {final_status}")
    else:
        print(f"Final status: {final_status}")

    # Try to cancel again (should fail since it's no longer processing)
    print(f"\n🛑 Attempting to cancel again (should fail)...")
    second_cancel = await client.call_tool("cancel_thread", {"thread_id": thread_id})

    # Parse second cancel result
    if hasattr(second_cancel, 'content') and second_cancel.content and second_cancel.content[0].text:
        try:
            second_data = json.loads(second_cancel.content[0].text)
            if second_data.get("success"):
                print(f"✅ Second cancel successful: {second_data.get('message')}")
            else:
                print(f"❌ Second cancel failed (expected): {second_data.get('error', 'Unknown error')}")
        except json.JSONDecodeError:
            print(f"Second cancel result: {second_cancel}")
    else:
        print(f"Second cancel result: {second_cancel}")

    print(f"\n🏁 Cancellation demo completed.")
    print("\nKey points about thread cancellation:")
    print("- Use start_thread_without_polling to enable cancellation during processing")
    print("- Can only cancel threads that are currently processing")
    print("- Cancellation stops the latest interaction in the thread")
    print("- Attempting to cancel a completed/cancelled thread will fail")
    print("- Cancelled threads can potentially be continued with new messages")

async def start_thread_without_polling_demo(client):
    """Demonstrate starting a thread without polling for completion."""
    print("\n" + "="*60)
    print("🚀 START THREAD WITHOUT POLLING DEMO")
    print("="*60)
    print("This demo shows how to start a thread and manually check its status.")

    # Start a thread without waiting for completion
    question = "What are the top 3 largest tables in my database? Include row counts and sizes."

    print(f"\n🚀 Starting thread without polling...")
    print(f"Question: {question}")

    result = await client.call_tool("start_thread_without_polling", {"message": question})
    print(f"Start result: {result}")

    # Parse the dictionary response
    if hasattr(result, 'content') and result.content and result.content[0].text:
        try:
            result_data = json.loads(result.content[0].text)

            if result_data.get("success"):
                thread_id = result_data.get("thread_id")
                print(f"✅ Thread started with ID: {thread_id}")

                # Display the immediate response (should just be thread info)
                print(f"\n📝 Immediate Response:")
                print(f"Thread ID: {thread_id}")
                print(f"Interaction ID: {result_data.get('interaction_id')}")
                print(f"Status: {result_data.get('status')}")
                print(f"Message: {result_data.get('message')}")
            else:
                print(f"❌ Failed to start thread: {result_data.get('error', 'Unknown error')}")
                return
        except json.JSONDecodeError:
            print("❌ Failed to parse response as JSON")
            return
    else:
        print("❌ Failed to start thread")
        return

    # Now manually check status multiple times
    print(f"\n📊 Manually checking thread status...")

    for i in range(5):  # Check up to 5 times
        print(f"\n--- Status Check {i+1} ---")
        status_result = await client.call_tool("get_thread_status", {"thread_id": thread_id})

        # Parse status response
        if hasattr(status_result, 'content') and status_result.content and status_result.content[0].text:
            try:
                status_data = json.loads(status_result.content[0].text)
                status = status_data.get('status', 'Unknown')
                interactions = status_data.get('interactions_count', 0)
                print(f"Status: {status} ({interactions} interactions)")

                if status == "complete":
                    print("✅ Thread completed!")
                    break
                else:
                    print("⏳ Thread still processing, waiting 3 seconds...")
                    await asyncio.sleep(3)
            except json.JSONDecodeError:
                print(f"Status: {status_result}")
                print("⏳ Thread still processing, waiting 3 seconds...")
                await asyncio.sleep(3)
        else:
            print(f"Status: {status_result}")
            print("⏳ Thread still processing, waiting 3 seconds...")
            await asyncio.sleep(3)
    else:
        print("⏰ Stopped checking after 5 attempts")

    # Try to continue the thread
    print(f"\n💬 Continuing thread with follow-up question...")
    follow_up = "Can you show me the schema of the largest table?"
    continue_result = await client.call_tool("continue_thread", {
        "thread_id": thread_id,
        "message": follow_up
    })

    # Parse continue result
    if hasattr(continue_result, 'content') and continue_result.content and continue_result.content[0].text:
        try:
            continue_data = json.loads(continue_result.content[0].text)
            if continue_data.get("success"):
                print(f"✅ Continue successful - Answer: {continue_data.get('answer', 'No answer')[:100]}...")
            else:
                print(f"❌ Continue failed: {continue_data.get('error', 'Unknown error')}")
        except json.JSONDecodeError:
            print(f"Continue result: {continue_result}")
    else:
        print(f"Continue result: {continue_result}")

    print(f"\n🏁 Start without polling demo completed.")
    print("\nKey points about starting without polling:")
    print("- Returns thread_id and interaction_id immediately")
    print("- Thread processing happens asynchronously")
    print("- Use get_thread_status to check progress")
    print("- Can continue threads even while they're processing")

async def artifact_demo(client):
    """Demonstrate artifact retrieval functionality."""
    print("\n" + "="*60)
    print("🎯 ARTIFACT RETRIEVAL DEMO")
    print("="*60)
    print("This demo shows how to retrieve artifacts created by threads.")
    print("We'll start a thread that creates files and then retrieve them.")
    print("="*60)

    # Start a thread that should create artifacts
    artifact_question = "Create a CSV file with sample sales data for the top 5 products. Include columns for product name, sales amount, and region."

    print(f"\n🚀 Starting thread to create artifacts...")
    print(f"Question: {artifact_question}")

    result = await client.call_tool("start_thread", {"message": artifact_question})

    # Parse the dictionary response
    if hasattr(result, 'content') and result.content and result.content[0].text:
        try:
            result_data = json.loads(result.content[0].text)

            if result_data.get("success"):
                thread_id = result_data.get("thread_id")
                artifacts = result_data.get("artifacts", [])

                print(f"✅ Thread completed with ID: {thread_id}")
                print(f"📎 Artifacts created: {len(artifacts)}")

                if artifacts:
                    # Test get_artifact with each artifact
                    for i, artifact in enumerate(artifacts, 1):
                        artifact_id = artifact.get('id') if isinstance(artifact, dict) else artifact
                        print(f"\n--- Artifact {i}: {artifact_id} ---")

                        artifact_result = await client.call_tool("get_artifact", {
                            "thread_id": thread_id,
                            "artifact_id": artifact_id
                        })

                        # Parse artifact result
                        if hasattr(artifact_result, 'content') and artifact_result.content and artifact_result.content[0].text:
                            try:
                                artifact_data = json.loads(artifact_result.content[0].text)
                                if artifact_data.get("success"):
                                    print(f"✅ Artifact retrieved successfully!")
                                    print(f"   Content Type: {artifact_data.get('content_type')}")
                                    print(f"   Size: {artifact_data.get('size')} bytes")

                                    # Show preview of data
                                    data = artifact_data.get("data", "")
                                    if isinstance(data, str):
                                        preview = data[:200] + "..." if len(data) > 200 else data
                                        print(f"   Data preview:\n{preview}")
                                    else:
                                        print(f"   Data type: {type(data)}")
                                        print(f"   Data preview: {str(data)[:100]}...")
                                else:
                                    print(f"❌ Failed to get artifact: {artifact_data.get('error')}")
                            except json.JSONDecodeError:
                                print(f"❌ Failed to parse artifact response")
                        else:
                            print(f"❌ No response from get_artifact")
                else:
                    print("ℹ️ No artifacts were created in this thread")

                    # Test with a non-existent artifact to show error handling
                    print(f"\n🔧 Testing error handling with non-existent artifact...")
                    error_result = await client.call_tool("get_artifact", {
                        "thread_id": thread_id,
                        "artifact_id": "non-existent-artifact-id"
                    })

                    if hasattr(error_result, 'content') and error_result.content and error_result.content[0].text:
                        try:
                            error_data = json.loads(error_result.content[0].text)
                            print(f"Expected error: {error_data.get('error')}")
                        except json.JSONDecodeError:
                            print(f"Error result: {error_result}")
            else:
                print(f"❌ Failed to start thread: {result_data.get('error', 'Unknown error')}")
                return
        except json.JSONDecodeError:
            print("❌ Failed to parse response as JSON")
            return
    else:
        print("❌ Failed to start thread")
        return

    print(f"\n🏁 Artifact demo completed.")
    print("\nKey points about artifact retrieval:")
    print("- Use get_artifact to retrieve files created by threads")
    print("- Artifacts have IDs that can be found in thread responses")
    print("- Supports various content types (CSV, JSON, text, etc.)")
    print("- Returns content type, size, and actual data")
    print("- Handles errors gracefully for non-existent artifacts")
    print("- Useful for non-blocking workflows")

if __name__ == "__main__":
    asyncio.run(main())
