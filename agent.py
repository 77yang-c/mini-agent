import json
import re
from llm import chat
from tools.base import Registry
from tools.fs import ReadFile
from tools.web import WebFetch, WebDo

def build_registry() -> Registry:
    reg = Registry()
    reg.add(ReadFile())
    reg.add(WebFetch())
    reg.add(WebDo())
    return reg

SYSTEM_PROMPT = """你是本地编程助手。你可以使用以下工具：
- read_file: 读取文件内容，参数 path
- web_fetch: 访问网页获取纯文本，参数 url
- web_do: 操作浏览器网页，参数 action（navigate/click/type/read/screenshot）及对应参数

当需要调用工具时，严格按以下格式输出（不要加其他内容）：

<tool_call>
{"name": "工具名", "arguments": {"参数": "值"}}
</tool_call>

每次只能调用一个工具。收到工具结果后继续对话。用中文回复。"""

# 兜底：从文本中解析 tool_call（qwen2.5:7b 不支持原生 tool_calls）
TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*\n?\s*(.*?)\s*\n?\s*</tool_call>", re.DOTALL
)
# 匹配裸 {"name": "...", "arguments": {...}} 格式的 JSON
RAW_TOOL_JSON_RE = re.compile(
    r'\{\s*"name"\s*:\s*"(\w+)"\s*,\s*"arguments"\s*:(.*?)\}\s*$', re.DOTALL
)

def parse_tool_call(text: str):
    """从文本中提取 JSON 工具调用，先试 <tool_call> 标签，再试裸 JSON"""
    m = TOOL_CALL_RE.search(text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    # 裸 JSON 兜底
    m = RAW_TOOL_JSON_RE.search(text)
    if m:
        name = m.group(1)
        try:
            args = json.loads(m.group(2))
        except json.JSONDecodeError:
            args = {}
        return {"name": name, "arguments": args}
    return None

def run_agent(user_text: str):
    reg = build_registry()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    for turn in range(20):
        msg = chat(messages, tools=reg.schema())
        messages.append(msg)

        content = msg.get("content") or ""

        # 优先用原生 tool_calls
        tool_calls_raw = msg.get("tool_calls") or []

        # 兜底：从 content 文本解析 <tool_call>
        parsed = None
        if not tool_calls_raw and content:
            parsed = parse_tool_call(content)
            if parsed:
                tool_calls_raw = [{"function": parsed}]

        # 既没有原生 tool_calls 也没有文本解析到 → 结束
        if not tool_calls_raw:
            if content:
                print("assistant>", content)
            break

        # 打印非 tool_call 部分的文本
        clean = TOOL_CALL_RE.sub("", content).strip()
        if clean:
            print("assistant>", clean)

        for tc in tool_calls_raw:
            fn = tc["function"]
            name = fn["name"]
            arguments = fn.get("arguments") or "{}"
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
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