from tools.base import BaseTool
from pathlib import Path

MAX_LINES = 200
MAX_CHARS = 50_000

class ReadFile(BaseTool):
    name = "read_file"
    description = """
        Read contents of a file. 
        Use when you need to understand existing code, 
        check configuration, or review file content before editing. 
        For large files, use start_line and end_line to read specific sections.
    """
    parameters = {
        "type": "object",
        "required": ["path"],
        "properties": {
            "path": {
                "type": "string",
                "description": "File path to read. e.g. 'src/main.py', 'README.md'"
            },
            "start_line": {
                "type": "integer",
                "description": "Start reading from this line. Default: 1"
            },
            "end_line": {
                "type": "integer",
                "description": "Stop reading at this line. Default: 200"
            }
        }
    }

    def handle(
        self,
        path: str,
        start_line: int = 1,
        end_line: int = None
    ) -> str:
        file = self.safe_path(path)

        if not file.exists():
            return f"File not found: {path}"

        if self.__is_sensitive(file):
            return f"'{path}' may contain secrets."

        try:
            lines = file.read_text(errors="ignore").splitlines()
        except Exception as e:
            return f"Error reading file: {e}"

        total_lines = len(lines)

        if end_line is None:
            end_line = start_line + MAX_LINES - 1

        end_line = min(end_line, total_lines)
        start_line = max(1, start_line)

        selected = lines[start_line - 1 : end_line]
        content = "\n".join(selected)

        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS]
            return (
                f"# {path} (lines {start_line}-{end_line}, truncated)\n"
                f"{content}\n\n"
                f"Content truncated at {MAX_CHARS} chars."
            )

        footer = ""
        if end_line < total_lines:
            footer = (
                f"\n\n--- {total_lines - end_line} more lines. "
                f"Use start_line={end_line + 1} to continue. ---"
            )

        return f"# {path} (lines {start_line}-{end_line} of {total_lines})\n{content}{footer}"

    def __is_sensitive(self, file: Path) -> bool:
        sensitive = {".env", ".pem", ".key", ".p12", "credentials.json"}
        return file.name in sensitive or file.name.startswith(".env")
