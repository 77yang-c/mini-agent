# Mini Agent

对接本地 Ollama（默认 `deepseek-r1:7b`）的最小 coding agent。

## 项目结构

```
mini-agent/
│
├── cli.py                    # 入口：交互循环，session 管理
├── agent.py                  # 核心：Agent 主循环、tool_call 解析、记忆编排
├── llm.py                    # 通信：httpx → Ollama /v1/chat/completions
├── config.py                 # 配置：base_url, model, max_turns
├── session.py                # 短期记忆：messages → JSON 持久化
│
├── memory/
│   └── long_term.py          # 长期记忆：ChromaDB + MiniLM 向量检索
│
├── tools/
│   ├── base.py               # 抽象：Tool(ABC) + Registry 注册中心
│   ├── fs.py                 # ReadFile：读本地文件
│   ├── writefile.py          # WriteFile：写本地文件
│   ├── web.py                # WebTool：fetch + Playwright 浏览器操作
│   └── shell.py              # RunShell：Shell 命令（危险拦截）
│
├── sessions/
│   └── last.json             # 短期会话文件（运行时生成）
│
├── memory_db/                # ChromaDB 向量库（运行时生成）
│
└── requirements.txt
```

## 流程图

```
┌──────────┐
│  用户输入  │
└────┬─────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│              cli.py                                      │
│  session_id = "last" (续聊) / None (新对话)               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              agent.py  run_agent()                       │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │ 1. 记忆注入                                       │   │
│  │    SessionStore.load() ← 恢复短期对话历史          │   │
│  │    LongMemory.recall() ← 检索长期相关记忆          │   │
│  └────────────────────┬─────────────────────────────┘   │
│                       │                                  │
│  ┌────────────────────▼─────────────────────────────┐   │
│  │ 2. Agent 循环 (最多 20 轮)                        │   │
│  │                                                   │   │
│  │   trim_messages() → 裁剪超长上下文                 │   │
│  │          │                                        │   │
│  │          ▼                                        │   │
│  │   chat(messages, tools) ──── llm.py ──── Ollama   │   │
│  │          │                                        │   │
│  │          ▼                                        │   │
│  │   返回 msg，有 tool_calls?                         │   │
│  │     │                                             │   │
│  │     ├─ 无 → 打印文本，break 结束                   │   │
│  │     │                                             │   │
│  │     └─ 有 → 遍历 tool_calls                       │   │
│  │               │                                   │   │
│  │               ▼                                   │   │
│  │          Registry.call(name, args)                │   │
│  │               │                                   │   │
│  │               ▼                                   │   │
│  │          Tool.run(args) ── 返回结果                │   │
│  │               │                                   │   │
│  │               ├─ 出错 → LongMemory.remember(error)│   │
│  │               │                                   │   │
│  │               ▼                                   │   │
│  │          结果作为 tool role 追加到 messages        │   │
│  │          循环继续 → 回到 chat()                    │   │
│  └────────────────────┬─────────────────────────────┘   │
│                       │                                  │
│  ┌────────────────────▼─────────────────────────────┐   │
│  │ 3. 记忆保存                                       │   │
│  │    LLM 总结对话 → LongMemory.remember(summary)    │   │
│  │    SessionStore.save() → 持久化短期消息            │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```


## 准备

1. 安装并启动 Ollama  
2. 确认模型：`ollama list`（需有 `deepseek-r1:7b`或`qwen2.5:7b`或者更高）  
3. 安装依赖：

```powershell
cd C:\Users\ycq\mini-agent
pip install -r requirements.txt
pip install chromadb sentence-transformers //长期记忆依赖
```

4. （可选）浏览网页功能需要 Playwright：

```powershell
pip install playwright
python -m playwright install chromium
```

## 运行

```powershell
# 交互
python cli.py

# 一次性任务
python cli.py "用 glob 列出当前目录下的 py 文件"

# 继续上次会话
python cli.py --session last

#新对话
python cli.py "new"
```

## 结构

| 文件 | 作用 |
|------|------|
| `config.py` | base_url / model / max_turns |
| `llm.py` | 调 `/v1/chat/completions` |
| `agent.py` | 主循环 |
| `cli.py` | 入口与 shell 审批 |
| `session.py` | 会话 JSON |
| `tools/*` | 读改文件、grep、shell |
| `memory/long_term.py` | 长期记忆(向量检索) |

## 记忆

| 类型 | 实现 | 说明 |
|------|------|------|
| 短期 | `session.py` → JSON | 对话历史持久化，续聊恢复 |
| 裁剪 | `trim_messages()` | 超 6000 token 自动裁旧消息 |
| 长期 | ChromaDB + MiniLM | 向量检索历史经验，含错误记录/自动总结 |

长记忆 3 个触发点：用户说"记住"、工具出错、对话结束 LLM 自动总结。

## 换模型

```powershell
$env:MINI_AGENT_MODEL = "deepseek-r1:7b"
$env:MINI_AGENT_MODEL = "qwen2.5:7b"
# 或换云端时改 base_url + api_key
