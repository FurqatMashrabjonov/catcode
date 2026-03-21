from abc import ABC, abstractmethod
from pathlib import Path

class BaseTool(ABC):
    name: str
    description: str
    parameters: dict

    def __init__(self, workdir: Path):
        self.workdir = workdir

    def safe_path(self, p: str) -> Path:
        path = (self.workdir / p).resolve()
        if not path.is_relative_to(self.workdir):
            raise ValueError(f"Path escapes workspace: {p}")

        return path

    @abstractmethod
    def handle(self, **kwargs):
        pass

    def to_llm(self):
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }