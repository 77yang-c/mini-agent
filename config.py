import os
from dataclasses import dataclass

@dataclass
class Settings:
    base_url: str ="http://localhost:11434/v1"
    api_key: str ="ollama"
    model: str ="qwen2.5:7b"
    max_turns: int = 20
    cwd: str = os.getcwd()
settings = Settings()