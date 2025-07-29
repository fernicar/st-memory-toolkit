#!/usr/bin/env python3
"""
Gemini API Test Script
"""

print("🧠 Testing Google Gemini API integration...")

try:
    from src.llm_client import GeminiClient
    from src.table_manager import TableManager
    from src.prompt_manager import PromptManager

    print("✅ Modules imported successfully")

    # Initialize components
    llm_client = GeminiClient()
    print(f"✅ Gemini client initialized: {'Success' if llm_client.is_available() else 'Failed'}")

    if llm_client.is_available():
        # Test simple conversation
        print("\n🤖 Testing simple conversation...")
        response = llm_client.generate_content("Hello, if you receive this, please reply: 'I would do anything for my country'")
        if response:
            print(f"✅ Received response: {response}")
        else:
            print("❌ No response received")

        # Test table operation prompt
        print("\n📊 Testing table operation prompt...")
        table_manager = TableManager()
        prompt_handler = PromptManager(table_manager)

        # Generate a prompt with table data
        test_conversation = "[user]: How are you today, Zhen Yinling?\n[assistant]: I'm fine, I was just practicing a song in the music room."
        full_prompt = prompt_handler.generate_prompt_with_tables(test_conversation)

        print(f"📝 Generated prompt length: {len(full_prompt)} characters")

        # Send to Gemini
        llm_response = llm_client.generate_content(full_prompt)

        if llm_response:
            print(f"✅ Received LLM response length: {len(llm_response)} characters")
            print(f"📄 Response content preview:\n{llm_response[:500]}...")

            # Try to parse table operations
            operations = prompt_handler.extract_table_operations(llm_response)
            print(f"🔧 Parsed {len(operations)} table operations")

            if operations:
                for i, op in enumerate(operations, 1):
                    print(f"  {i}. {op}")

                # Execute operations
                results = prompt_handler.execute_operations(operations)
                success_count = sum(results)
                print(f"✅ Successfully executed {success_count}/{len(operations)} operations")

        else:
            print("❌ No LLM response received")

    else:
        print("⚠️ Gemini client not available, please check API key and network connection")

    print("\n🎉 Test complete!")

except Exception as e:
    print(f"❌ Test failed: {e}")
    import traceback
    traceback.print_exc()