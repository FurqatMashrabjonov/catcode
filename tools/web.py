from tools.base import BaseTool

class Web(BaseTool):
    name: str
    description: str
    parameters: dict

    def definition(self):
        return "This is Web tool"

    def handle(self, **kwargs):
        pass
