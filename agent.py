from llm import chat
from tools.base import Registry
from tools.fs import ReadFile

def build_registry() -> Registry:
    reg = Registry()
    reg.add(ReadFile())
    return reg

SYSTEM_PROMPT = """你是本地编程助手。可以用工具读文件，当你需要读取文件内容时，请使用 read_file 工具，参数为文件的路径。用中文回复。"""

def run_agent(user_text: str):
    reg = build_registry()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    # 最多循环 20 轮，防止无限调用
    for turn in range(20):
        # 调用 LLM，传入工具 schema
        msg = chat(messages, tools=reg.schema())

        # 将 assistant 的原始回复（可能包含 tool_calls）加入历史
        messages.append(msg)

        # 如果有直接文本回复，打印出来
        content = msg.get("content")
        if content:
            print("assistant>", content)

        # 检查是否有工具调用
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            # 没有工具调用，结束循环
            break

        # 执行所有工具调用
        for tc in tool_calls:
            fn = tc["function"]
            name = fn["name"]
            arguments = fn.get("arguments") or "{}"
            # 调用工具，获取结果（字符串）
            try:
                result = reg.call(name, arguments)
            except Exception as e:
                result = f"工具执行出错: {str(e)}"
            print(f"[tool] {name} -> {result[:200]}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", name),
                "content": result,
            })
        # 循环继续，将工具结果发回模型，生成最终回复

    # 如果循环结束（超过20轮），可打印提示，但不影响
    # 可选择返回最后一条消息
    #return messages[-1]  # 如果需要外部获取