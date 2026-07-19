import json
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union

class Tool(ABC):
    name: str
    description: str
    parameters: dict

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            },
        }
    @abstractmethod
    def run(self, args: dict) -> str:
        """执行工具逻辑，返回字符串结果"""
        pass

class Registry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
    
    def add(self, tool: Tool):
        self.tools[tool.name] = tool

    def schema(self) -> List[dict]:
        return [tool.schema() for tool in self.tools.values()]
    
    def call(self, name: str, arguments: Union[str, dict]) -> str:
        """调用工具，arguments 为 JSON 字符串或 dict"""
        if name not in self.tools:
            return f"ERROR: unknown tool '{name}'"
        
        # 解析参数
        if isinstance(arguments, str):
            try:
                args = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError as e:
                return f"ERROR: 工具参数解析失败: {arguments}\n错误: {e}"
        else:
            args = arguments  # 如果直接传入 dict
        
        # 执行工具
        try:
            result = self.tools[name].run(args)
            # 确保返回字符串
            return str(result) if result is not None else ""
        except Exception as e:
            return f"ERROR: 工具执行异常 {type(e).__name__}: {e}"