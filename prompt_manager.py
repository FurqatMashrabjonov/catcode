from pathlib import Path

class PromptManager:
    def get(self, type: str):
        if type not in ['agent', ...]:
            raise Exception("type is not in prompts")

        return self.__get_content(f"{type.upper()}.md")


    def __get_content(self, path: str):
        file = Path(f"./prompts/{path}")
        if not file.exists():
            raise Exception(f"{path} not exists")

        return file.read_text(errors="ignore")

