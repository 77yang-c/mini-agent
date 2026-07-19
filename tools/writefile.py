from pathlib import Path
from tools.base import Tool
from config import settings


class WriteFile(Tool):
    name = "write_file"
    description = "创建或覆盖写入文件，传入文件路径和内容"
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "文件路径"},
            "content": {"type": "string", "description": "要写入的内容"},
        },
        "required": ["path", "content"],
    }

    def run(self, args: dict) -> str:
        p = Path(args["path"])
        # 1. 相对路径 → 基于工作目录
        if not p.is_absolute():
            p = Path(settings.cwd) / p
        p = p.resolve()

        # 2. 安全检查：禁止写入工作目录之外
        if not str(p).startswith(str(Path(settings.cwd).resolve())):
            return "ERROR: 禁止写出工作目录"

        # 3. 写入文件
        content = args["content"]
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"已写入 {p}，{len(content)} 字符"
