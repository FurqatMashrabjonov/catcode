from tools.base import BaseTool
import subprocess


class RunTerminal(BaseTool):
    name = "run_terminal"
    description = """
        Execute a bash command in the terminal. 
        Use for: running tests, installing packages, 
        git operations, creating folders, running scripts. 
        Avoid destructive commands like rm -rf, sudo, chmod.
        Use only for local project tasks (tests, git, artisan). NEVER use for internet research.
    """
    parameters = {
        "type": "object",
        "required": ["command"],
        "properties": {
            "command": {
                "type": "string",
                "description": (
                    "Bash command to execute. "
                )
            },
            "timeout": {
                "type": "integer",
                "description": "Max seconds to wait. Default 30. Use 120 for long installs."
            },
            "working_dir": {
                "type": "string",
                "description": "Directory to run command in. Default is project root."
            }
        }
    }

    BLOCKED = ["rm -rf", "sudo", "mkfs", "dd if=", ":(){:|:&};:"]

    def handle(
        self,
        command: str,
        timeout: int = 30,
        working_dir: str = "."
    ) -> str:

        for blocked in self.BLOCKED:
            if blocked in command:
                return f"'{blocked}' is not allowed."

        run_path = self.safe_path(working_dir)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(run_path)
            )

            output = ""

            if result.stdout:
                output += result.stdout

            if result.stderr:
                output += f"\nSTDERR:\n{result.stderr}"

            if not output:
                return "Command executed. No output."

            lines = output.splitlines()
            if len(lines) > 100:
                return (
                    "\n".join(lines[:100]) +
                    f"\n\n... {len(lines) - 100} more lines truncated."
                )

            return output

        except subprocess.TimeoutExpired:
            return f"Timeout: command exceeded {timeout}s."

        except Exception as e:
            return f"Error: {e}"