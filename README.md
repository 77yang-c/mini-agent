# Mini Agent

对接本地 Ollama（默认 `deepseek-r1:7b`）的最小 coding agent。

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

## 换模型

```powershell
$env:MINI_AGENT_MODEL = "deepseek-r1:7b"
$env:MINI_AGENT_MODEL = "qwen2.5:7b"
# 或换云端时改 base_url + api_key
