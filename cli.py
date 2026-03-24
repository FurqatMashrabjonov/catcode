import sys
from rich.console import Console, Group
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.align import Align
from rich.prompt import Prompt


class Cli:
    def __init__(self):
        self.console = Console()

    def render_body(self, text, usage=None):
        token_info = ""
        if usage:
            token_info = f"[dim]Tokens: ⬇ {usage.input_readable} | ⬆ {usage.output_readable} | ↕ {usage.total_readable}[/dim]"

        content_group = Group(
            Panel(
                Markdown(text),
                subtitle=token_info,
                subtitle_align="right",
                border_style="bright_black",
            )
        )
        return Align.left(content_group)

    def run(self, agent):
        cat_logo = """
    [bold dark_orange]
      ██     ██
      █████████
      █ ▄   ▄ █
      █   ▀   █
      █████████
    [/bold dark_orange]
    [bold cyan]    CatCode   [/bold cyan]
    """
        self.console.print(Align.center(cat_logo))

        self.console.print(Align.center("[italic dim]Welcome to CatCode - Your AI coding assistant[/italic dim]\n"))
        self.console.print("[bold blue]Ctrl+C to exit.[/bold blue]\n")

        try:
            while True:
                user_input = Prompt.ask("[bold cyan]Ask[/bold cyan]")

                if not user_input.strip():
                    continue

                with Live(console=self.console, refresh_per_second=2.5, vertical_overflow="visible") as live:
                    live.update(Panel("[italic dim]Thinking...[/italic dim]", border_style="bright_black"))

                    output, token_usage = agent.ask(user_input)

                    live.update(self.render_body(output, token_usage))

                self.console.print()

        except KeyboardInterrupt:
            self.console.print("\n[bold red]Exit[/bold red]")
            sys.exit(0)