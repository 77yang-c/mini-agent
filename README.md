# Mini Agent

对接本地 Ollama（默认 `deepseek-r1:7b`）的最小 coding agent。

## 准备

1. 安装并启动 Ollama  
2. 确认模型：`ollama list`（需有 `deepseek-r1:7b`）  
3. 安装依赖：

```powershell
cd C:\Users\ycq\mini-agent
pip install -r requirements.txt
```

## 运行

```powershell
# 交互
python cli.py

# 一次性任务
python cli.py "用 glob 列出当前目录下的 py 文件"

# 继续上次会话
python cli.py --session last
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

## 换模型

```powershell
$env:MINI_AGENT_MODEL = "deepseek-r1:7b"
# 或换云端时改 base_url + api_key
```
