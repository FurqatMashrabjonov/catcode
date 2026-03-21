from pathlib import Path
from typing import Any, Dict, List, Type

from tools.read_file import ReadFile
from tools.search_code import SearchCode
from tools.run_terminal import RunTerminal

class Tool:
    def __init__(self, workdir: Path):
        self.workdir = workdir
        
        tool_classes: List[Type] = [
            ReadFile,
            SearchCode,
            RunTerminal,
        ]

        self._tools = {
            cls.name: cls(workdir=self.workdir) for cls in tool_classes
        }

    def get_tools(self) -> List[Dict[str, Any]]:
        return [tool.to_llm() for tool in self._tools.values()]

    def run(self, name: str, args: Dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool named '{name}' not found."

        try:
            return tool.handle(**args)
        except Exception as e:
            return f"Error executing tool '{name}': {str(e)}"
