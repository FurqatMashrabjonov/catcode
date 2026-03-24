from pathlib import Path
from typing import Any, Dict, List, Type

from tools.read_file import ReadFile
from tools.search_code import SearchCode
from tools.run_terminal import RunTerminal
from tools.todo import Todo
from tools.compact import Compact

MAX_OUTPUT = 3000

class ToolManager:
    def __init__(self, workdir: Path):
        self.workdir = workdir
        
        tool_classes: List[Type] = [
            ReadFile,
            SearchCode,
            RunTerminal,
            Todo,
            Compact
        ]

        self._tools = {
            cls.name: cls(workdir=self.workdir) for cls in tool_classes
        }

    def get_tools(self) -> List:
        return [tool.to_llm() for tool in self._tools.values()]

    def run(self, name: str, args: Dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool named '{name}' not found."

        try:
            return tool.handle(**args)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"

    def _trim(self, name: str, result: str) -> str:
        if len(result) <= MAX_OUTPUT:
            return result

        if name == "run_terminal":
            lines = result.splitlines()
            if len(lines) > 40:
                head = "\n".join(lines[:10])
                tail = "\n".join(lines[-20:])
                return f"{head}\n\n[...{len(lines) - 30} lines skipped...]\n\n{tail}"

        return result[:MAX_OUTPUT] + f"\n[...truncated]"