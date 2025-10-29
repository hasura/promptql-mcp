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
            
                # Choose interaction mode
                print("\nChoose interaction mode:")
                print("1. Multi-turn conversation (thread-based)")
                print("2. Thread management demo")
                print("3. Thread cancellation demo")
                print("4. Start thread without polling demo")
                mode = input("Enter choice (1, 2, 3, or 4): ").strip()

                if mode == "1":
                    await multi_turn_conversation(client)
                elif mode == "2":
                    await thread_management_demo(client)
                elif mode == "3":
                    await thread_cancellation_demo(client)
                elif mode == "4":
                    await start_thread_without_polling_demo(client)
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

            # Access result directly without extract_result_text
            if hasattr(result, 'content') and result.content and result.content[0].text:
                result_text = result.content[0].text

                if "Thread ID:" in result_text:
                    thread_id = result_text.split("Thread ID: ")[1].split("\n")[0].strip()
                    conversation_count += 1
                    print(f"✅ Thread started with ID: {thread_id}")

                    # Display the complete response (start_thread now waits for completion)
                    print(f"\n📝 Response:")
                    print(result_text)
                else:
                    print("❌ Failed to start thread")
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
                print(f"📊 Thread status: {status_result}")
                continue

            print(f"\n💬 Continuing thread {thread_id}...")
            result = await client.call_tool("continue_thread", {
                "thread_id": thread_id,
                "message": question
            })
            conversation_count += 1
            print(f"\n📝 Response:")
            print(result)

    if thread_id:
        print(f"\n🏁 Conversation ended. Final thread ID: {thread_id}")
        print(f"📈 Total questions asked: {conversation_count}")

        # Get final status
        final_status = await client.call_tool("get_thread_status", {"thread_id": thread_id})
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

    # Access result directly without extract_result_text
    if hasattr(result, 'content') and result.content and result.content[0].text:
        result_text = result.content[0].text

        if "Thread ID:" in result_text:
            thread_id = result_text.split("Thread ID: ")[1].split("\n")[0].strip()
            print(f"✅ Thread started with ID: {thread_id}")

            # Display the complete initial response (start_thread now waits for completion)
            print(f"\n📝 Initial Response:")
            print(result_text)

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
            print(f"Pre-continue status: {pre_status}")

            # Use continue_thread to maintain context
            continue_result = await client.call_tool("continue_thread", {
                "thread_id": thread_id,
                "message": question
            })
            print(f"Continue result: {continue_result}")

            # Check status after each continuation
            status_result = await client.call_tool("get_thread_status", {"thread_id": thread_id})
            print(f"📊 Post-continue status: {status_result}")

            # Small delay between questions
            await asyncio.sleep(2)

        print(f"\n🏁 Demo completed. Used continue_thread {len(follow_up_questions)} times on thread {thread_id[:8]}...")

    else:
        print("❌ Failed to start initial thread")

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

    # Access result directly without extract_result_text
    if hasattr(result, 'content') and result.content and result.content[0].text:
        result_text = result.content[0].text

        if "Thread ID:" in result_text:
            thread_id = result_text.split("Thread ID: ")[1].split("\n")[0].strip()
            print(f"✅ Thread started with ID: {thread_id}")

            # Display the immediate response (should just be thread info)
            print(f"\n📝 Immediate Response:")
            print(result_text)

        # Give the thread a moment to start processing
        print("\n⏳ Waiting 3 seconds for processing to begin...")
        await asyncio.sleep(3)

        # Check status (should be processing)
        print("\n📊 Checking thread status...")
        status_result = await client.call_tool("get_thread_status", {"thread_id": thread_id})
        print(f"Status: {status_result}")

        # Attempt to cancel while processing
        print(f"\n🛑 Attempting to cancel thread {thread_id} while processing...")
        cancel_result = await client.call_tool("cancel_thread", {"thread_id": thread_id})
        print(f"Cancel result: {cancel_result}")

        # Check status after cancellation
        print("\n📊 Checking thread status after cancellation...")
        final_status = await client.call_tool("get_thread_status", {"thread_id": thread_id})
        print(f"Final status: {final_status}")

        # Try to cancel again (should fail since it's no longer processing)
        print(f"\n🛑 Attempting to cancel again (should fail)...")
        second_cancel = await client.call_tool("cancel_thread", {"thread_id": thread_id})
        print(f"Second cancel result: {second_cancel}")

    else:
        print("❌ Failed to start thread")

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

    # Access result directly without extract_result_text
    if hasattr(result, 'content') and result.content and result.content[0].text:
        result_text = result.content[0].text

        if "Thread ID:" in result_text:
            thread_id = result_text.split("Thread ID: ")[1].split("\n")[0].strip()
            print(f"✅ Thread started with ID: {thread_id}")

            # Display the immediate response (should just be thread info)
            print(f"\n📝 Immediate Response:")
            print(result_text)

        # Now manually check status multiple times
        print(f"\n📊 Manually checking thread status...")

        for i in range(5):  # Check up to 5 times
            print(f"\n--- Status Check {i+1} ---")
            status_result = await client.call_tool("get_thread_status", {"thread_id": thread_id})
            print(f"Status: {status_result}")

            # Check if the status indicates completion
            if hasattr(status_result, 'content') and status_result.content and status_result.content[0].text:
                status_text = status_result.content[0].text
                if '"status": "complete"' in status_text or 'status: complete' in status_text.lower():
                    print("✅ Thread completed!")
                    break
            else:
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
        print(f"Continue result: {continue_result}")

    else:
        print("❌ Failed to start thread")

    print(f"\n🏁 Start without polling demo completed.")
    print("\nKey points about starting without polling:")
    print("- Returns thread_id and interaction_id immediately")
    print("- Thread processing happens asynchronously")
    print("- Use get_thread_status to check progress")
    print("- Can continue threads even while they're processing")
    print("- Useful for non-blocking workflows")

if __name__ == "__main__":
    asyncio.run(main())
