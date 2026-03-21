from tools.base import BaseTool
import subprocess
from pathlib import Path


class SearchCode(BaseTool):
    name = "search_code"
    description = """
        Search for a keyword or pattern inside project files. 
        Use to find function definitions, class usages, imports, 
        or any text across the codebase. 
        Returns file path, line number, and matching line content.
    """
    parameters = {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Text or pattern to search. "
                    "e.g. 'def authenticate', 'import fastapi', 'Route::get'"
                )
            },
            "path": {
                "type": "string",
                "description": (
                    "Directory to search in. Default is current project root '.'"
                )
            },
            "file_pattern": {
                "type": "string",
                "description": (
                    "Filter by file extension. "
                    "e.g. '*.py', '*.js', '*.php'"
                )
            }
        }
    }

    def handle(self, query: str, path: str = ".", file_pattern: str = None) -> str:
        search_path = str(self.safe_path(path))
        folders, files = self.__get_ignore_paths()

        cmd = ["grep", "-r", "-n", query, search_path]

        for folder in folders:
            cmd.append(f"--exclude-dir={folder}")

        for file in files:
            cmd.append(f"--exclude={file}")

        if file_pattern:
            cmd.append(f"--include={file_pattern}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15
            )
        except subprocess.TimeoutExpired:
            return "Search timed out after 15 seconds. Try a more specific query."
        except Exception as e:
            return f"Search failed: {e}"

        if not result.stdout:
            return "No results found."

        lines = result.stdout.splitlines()

        if len(lines) > 50:
            return (
                "\n".join(lines[:50]) +
                f"\n\n[{len(lines) - 50} more results omitted. Refine your query.]"
            )

        return "\n".join(lines)

    def __get_ignore_paths(self) -> tuple[list[str], list[str]]:
        gitignore = self.workdir / ".gitignore"

        if not gitignore.exists():
            return [], []

        folders = []
        files = []

        for line in gitignore.read_text().splitlines():
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if line.endswith("/"):
                folders.append(line.rstrip("/"))
            else:
                files.append(line)

        return folders, files