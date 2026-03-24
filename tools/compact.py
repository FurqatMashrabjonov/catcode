from typing import Any, Dict
from tools.base import BaseTool

class Compact(BaseTool):
    name = "compact"
    description = "Trigger manual conversation compression. Use this when the history becomes too long or irrelevant."

    def to_llm(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "focus": {
                        "type": "string",
                        "description": "What to preserve in the summary"
                    }
                }
            }
        }

    def handle(self, focus: str = None) -> str:
        return f"Manual compression requested. Focus: {focus if focus else 'none'}"
