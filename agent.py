import json
import re
from llm import chat
from tools.base import Registry
from tools.fs import ReadFile
from tools.web import WebTool
from tools.writefile import WriteFile
from session import SessionStore
from memory.long_term import LongMemory

def build_registry() -> Registry:
    reg = Registry()
    reg.add(ReadFile())
    reg.add(WebTool())
    reg.add(WriteFile())
    return reg

SYSTEM_PROMPT = """你是本地编程助手，可以用工具完成文件读写和网页操作。

## 工具说明

### read_file
读取本地文件内容。
参数：path（文件路径，必填）

### writefile
创建或覆盖写入文件，传入文件路径和内容
参数：path（文件路径，必填）

### web
网页工具，通过 action 参数选择操作：
- fetch    抓取网页纯文本        参数：url
- navigate 浏览器打开网页        参数：url
- type     在输入框中填写内容     参数：selector（CSS选择器）+ text（输入内容）
- click    点击按钮/链接         参数：selector（CSS选择器）
- read     读取当前页面纯文本     无额外参数

## 网页操作流程

登录网站等复杂操作必须分步执行，每步一次工具调用：
1. 先 navigate 打开目标网址
2. 再 type 填写账号、密码等
3. 然后 click 点击登录/提交按钮
4. 最后 read 读取结果页面

收到每一步的工具返回结果后，再执行下一步。

## 输出格式

调用工具时严格输出：
<tool_call>
{"name": "工具名", "arguments": {"参数名": "参数值"}}
</tool_call>

不调用工具时直接文本回复。用中文回复。"""

# 兜底：从文本中解析 tool_call（qwen2.5:7b 不支持原生 tool_calls）
TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*\n?\s*(.*?)\s*\n?\s*</tool_call>", re.DOTALL
)

def _find_json_blocks(text: str):
    """用大括号计数提取所有顶层 JSON 对象"""
    results = []
    i = 0
    while i < len(text):
        # 找 {"name":
        start = text.find('{"name":', i)
        if start == -1:
            break
        depth = 0
        j = start
        while j < len(text):
            c = text[j]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    results.append(text[start:j + 1])
                    i = j + 1
                    break
            j += 1
        else:
            # 没找到配对的 }
            break
    return results

def parse_tool_calls(text: str):
    """从文本中提取所有工具调用"""
    calls = []
    # 1. <tool_call> 标签
    for m in TOOL_CALL_RE.finditer(text):
        try:
            calls.append(json.loads(m.group(1)))
        except json.JSONDecodeError:
            pass
    if calls:
        return calls
    # 2. 裸 JSON 括号配对
    for block in _find_json_blocks(text):
        try:
            obj = json.loads(block)
            if "name" in obj and "arguments" in obj:
                calls.append(obj)
        except json.JSONDecodeError:
            pass
    return calls

def run_agent(user_text: str, session_id: str = None):
    stote = SessionStore("sessions")#短期记忆，恢复历史消息

    reg = build_registry()

    lmem = LongMemory()  # 长期记忆

    # ── 注入时机：每轮对话前检索相关记忆 ──
    recalled = ""
    try:
        memories = lmem.recall(user_text)
        if memories:
            recalled = "\n[历史相关经验]\n" + "\n".join(f"- {m}" for m in memories)
    except Exception:
        pass  # 首次使用模型未下载完成时忽略

    #恢复历史消息
    if session_id:
        try:
            messages = stote.load(session_id)
            messages.append({"role":"user","content":user_text})
        except FileNotFoundError:
            messages = [
                {"role":"system","content":SYSTEM_PROMPT + recalled},
                {"role":"user","content":user_text},
            ]
    else:
        messages = [
            {"role":"system","content":SYSTEM_PROMPT + recalled},
            {"role":"user","content":user_text},
        ]

    for turn in range(20):
        messages = trim_messages(messages)#短期会话裁剪
        msg = chat(messages, tools=reg.schema())
        messages.append(msg)

        content = msg.get("content") or ""

        # ── 触发1：用户明确说"记住" → 写入长期记忆 ──
        if content and "记住" in user_text:
            try:
                lmem.remember(user_text, tags=["user_cmd"])
            except Exception:
                pass

        # 优先用原生 tool_calls
        tool_calls_raw = msg.get("tool_calls") or []

        # 兜底：从 content 文本解析
        parsed = []
        if not tool_calls_raw and content:
            parsed = parse_tool_calls(content)
            if parsed:
                tool_calls_raw = [{"function": p} for p in parsed]

        # 既没有原生 tool_calls 也没有文本解析到 → 结束
        if not tool_calls_raw:
            if content:
                print("assistant>", content)
            break

        # 打印非 tool_call 部分的文本
        clean = TOOL_CALL_RE.sub("", content)
        for block in _find_json_blocks(content):
            clean = clean.replace(block, "")
        clean = clean.strip()
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
                # ── 触发2：工具出错 → 记录错误经验 ──
                try:
                    lmem.remember(f"[错误] 工具:{name} 参数:{arguments} 错误:{e}", tags=["error"])
                except Exception:
                    pass
            print(f"[tool] {name} -> {result[:200]}")
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", name),
                "content": result,
            })

    # ── 触发3：对话结束 → LLM 总结值得记住的内容 ──
    if session_id:
        has_tools = any(m.get("role") == "tool" for m in messages)
        if has_tools:
            try:
                msgs = messages[:1] + [{"role":"user","content":"用一句话中文总结本次对话中值得记住的用户偏好、操作习惯或重要信息。不超过50字。"}]
                summary = chat(msgs).get("content","")
                if summary and len(summary) > 5:
                    lmem.remember(summary, tags=["auto_summary"])
            except Exception:
                pass

    #保存
    if session_id:
        stote.save(session_id, messages)



#短期记忆裁剪
def trim_messages(messages, max_tokens=6000):
    total = sum(len(str(m.get("content","")))for m in messages)
    while total > max_tokens*1.5 and len(messages) > 3:
        removed = messages.pop(1)
        total -= len(str(removed.get("content","")))
    return messages