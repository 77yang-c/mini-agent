from pathlib import Path
from tools.base import Tool
from config import settings

class ReadFile(Tool):
    name = "read_file"
    description = "阅读文件"
    parameters = {
        "type": "object",
        "properties":{"path":{"type":"string"}},
        "required": ["path"],
    }

    def run(self, args:dict)->str:
        p=Path(args["path"])
        if not p.is_absolute():
            p=Path(settings.cwd)/p
        p=p.resolve()   #建议：拒绝cmd以外的路径
        text=p.read_text(encoding="utf-8", errors="replace")
        return text[:60000]#防止过长
    


def run(self, args:dict)->str:
    cmd = args["command"]
    ok = input(f"执行？{cmd}[y/N]").strip().lower in ("y","yes")
    if not ok:
        return "ERROR： user denied"