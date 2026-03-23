from typing import List

from tools.base import BaseTool

class Todo(BaseTool):
    name = "todo"
    description = """
       Update task list. Track progress on multi-step tasks.
       Rules: 
            1. The number of todo items should not be up on 20 
    """
    parameters = {
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "description": "List of todo items to write",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "string",
                            "description": "Unique identifier for the todo item, for example 1,2,3..."
                        },
                        "text": {
                            "type": "string",
                            "description": "The todo item description"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"],
                            "description": "Current status of the item"
                        }
                    },
                    "required": ["id", "text", "status"]
                }
            }
        }
    }

    def handle(self, items: List[dict]) -> str:
        todos = []
        str = ''
        for item in items:
            todo = f"{item['id']}. {item['text']} : {item['status']}"
            todos.append(todo)
            str += todo
            print(todo)

        return f"Todos updated: {str}"