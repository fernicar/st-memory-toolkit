#!/usr/bin/env python3
"""
Gemini API 测试脚本
"""

print("🧠 测试 Google Gemini API 集成...")

try:
    from src.llm_client import GeminiClient
    from src.table_manager import TableManager
    from src.prompt_handler import PromptHandler

    print("✅ 模块导入成功")

    # 初始化组件
    llm_client = GeminiClient()
    print(f"✅ Gemini客户端初始化: {'成功' if llm_client.is_available() else '失败'}")

    if llm_client.is_available():
        # 测试简单对话
        print("\n🤖 测试简单对话...")
        response = llm_client.generate_response("你好，收到请回复：'苟利国家生死以'")
        if response:
            print(f"✅ 收到响应: {response}")
        else:
            print("❌ 未收到响应")

        # 测试表格操作提示词
        print("\n📊 测试表格操作提示词...")
        table_manager = TableManager()
        prompt_handler = PromptHandler(table_manager)

        # 生成包含表格数据的提示词
        test_conversation = "[user]: 真银铃，你今天怎么样？\n[assistant]: 我很好，刚刚在音乐教室练歌。"
        full_prompt = prompt_handler.generate_prompt_with_tables(test_conversation)

        print(f"📝 生成的提示词长度: {len(full_prompt)} 字符")

        # 发送给Gemini
        llm_response = llm_client.generate_response(full_prompt)

        if llm_response:
            print(f"✅ 收到LLM响应长度: {len(llm_response)} 字符")
            print(f"📄 响应内容预览:\n{llm_response[:500]}...")

            # 尝试解析表格操作
            operations = prompt_handler.extract_table_operations(llm_response)
            print(f"🔧 解析到 {len(operations)} 个表格操作")

            if operations:
                for i, op in enumerate(operations, 1):
                    print(f"  {i}. {op}")

                # 执行操作
                results = prompt_handler.execute_operations(operations)
                success_count = sum(results)
                print(f"✅ 成功执行 {success_count}/{len(operations)} 个操作")

        else:
            print("❌ 未收到LLM响应")

    else:
        print("⚠️ Gemini客户端不可用，请检查API密钥和网络连接")

    print("\n🎉 测试完成！")

except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()