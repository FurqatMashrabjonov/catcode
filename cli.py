from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog, Static, Label
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.binding import Binding
from textual.reactive import reactive
from textual import work
from textual.worker import Worker
from rich.text import Text
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
import asyncio
import time
import random


CATCODE_CSS = """
Screen {
    background: #0a0a0f;
    layers: base overlay;
}

#sidebar {
    width: 22;
    background: #0f0f1a;
    border-right: solid #1e1e3a;
    padding: 1 1;
    height: 100%;
}

#sidebar-title {
    color: #a78bfa;
    text-style: bold;
    margin-bottom: 1;
    padding: 0 1;
}

.session-item {
    color: #6b7280;
    padding: 0 1;
    height: 1;
}

.session-item:hover {
    color: #e2e8f0;
    background: #1e1e3a;
}

.session-active {
    color: #a78bfa;
    background: #1e1e3a;
}

#main {
    background: #0a0a0f;
    height: 100%;
}

#chat-area {
    height: 1fr;
    padding: 1 3;
    background: #0a0a0f;
}

#messages {
    height: 1fr;
    background: #0a0a0f;
    scrollbar-color: #1e1e3a #0a0a0f;
}

#input-area {
    height: auto;
    padding: 1 3 1 3;
    background: #0a0a0f;
    border-top: solid #1e1e3a;
}

#input-box {
    background: #111122;
    border: solid #2a2a4a;
    color: #e2e8f0;
    padding: 0 1;
    height: 3;
}

#input-box:focus {
    border: solid #a78bfa;
}

#input-hint {
    color: #374151;
    padding: 0 1;
    height: 1;
}

#header-bar {
    height: 3;
    background: #0a0a0f;
    border-bottom: solid #1e1e3a;
    padding: 0 3;
    align: left middle;
}

#model-badge {
    background: #1e1e3a;
    color: #a78bfa;
    padding: 0 2;
    height: 1;
    content-align: center middle;
}

#status-dot {
    color: #10b981;
    width: 3;
    content-align: center middle;
}

.msg-user {
    background: #111122;
    border-left: thick #a78bfa;
    padding: 1 2;
    margin: 1 0;
    color: #e2e8f0;
}

.msg-assistant {
    background: #0d1117;
    border-left: thick #10b981;
    padding: 1 2;
    margin: 1 0;
    color: #d1d5db;
}

.msg-label-user {
    color: #a78bfa;
    text-style: bold;
    margin-bottom: 0;
}

.msg-label-assistant {
    color: #10b981;
    text-style: bold;
    margin-bottom: 0;
}

.thinking {
    color: #4b5563;
    text-style: italic;
    padding: 0 2;
    margin: 0 0 1 0;
}

#welcome {
    padding: 3 4;
    color: #4b5563;
    content-align: center middle;
    height: 100%;
}

.welcome-title {
    color: #a78bfa;
    text-style: bold;
    text-align: center;
}

.welcome-sub {
    color: #374151;
    text-align: center;
}
"""


FAKE_RESPONSES = [
    """I've analyzed your codebase. Here's what I found:

**`agent.py`** — Main agent loop with Gemini integration
**`tool_manager.py`** — Tool registry and dispatcher  
**`tools/`** — Individual tool implementations

The architecture looks clean. `BaseTool` abstraction with `safe_path` 
is a solid pattern for workspace isolation.""",

    """I'll search the codebase for that pattern.

Running `search_code` → found 4 occurrences across 2 files.

The issue is in `tools/search_code.py` line 22 — the `--exclude-dir` 
flags are being concatenated instead of appended as separate args.

Fixed version:
```python
for folder in folders:
    cmd.append(f"--exclude-dir={folder}")
```""",

    """Here's the optimized version of `tool_manager.py`:

```python
from pathlib import Path
from tools.read_file import ReadFile
from tools.search_code import SearchCode
from tools.shell import Shell

class Tool:
    def __init__(self, workdir: Path):
        self._tools = {
            t.name: t for t in [
                ReadFile(workdir),
                SearchCode(workdir),
                Shell(workdir),
            ]
        }

    def get_tools(self) -> list:
        return [
            {"name": t.name, "description": t.description,
             "parameters": t.parameters}
            for t in self._tools.values()
        ]

    def run(self, name: str, args: dict) -> str:
        if name not in self._tools:
            return f"Unknown tool: {name}"
        return self._tools[name].handle(**args)
```

Key improvements: dict comprehension, cleaner structure.""",
]

TOOL_CALLS = [
    "search_code({'query': 'BaseTool'})",
    "read_file({'path': 'tool_manager.py'})",
    "run_terminal({'command': 'find . -name \"*.py\"'})",
    "search_code({'query': 'def handle', 'file_pattern': '*.py'})",
]

SESSIONS = [
    "CatCode architecture",
    "Fix search_code bug",
    "Add memory layer",
    "Optimize tool loop",
    "Write README",
]


class MessageWidget(Static):
    def __init__(self, role: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.content = content

    def compose(self) -> ComposeResult:
        if self.role == "user":
            yield Label("You", classes="msg-label-user")
            yield Static(self.content, classes="msg-user")
        else:
            yield Label("CatCode", classes="msg-label-assistant")
            yield Static(self.content, classes="msg-assistant")


class CatCodeApp(App):
    CSS = CATCODE_CSS

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit"),
        Binding("ctrl+l", "clear", "Clear"),
        Binding("escape", "blur_input", "Blur"),
    ]

    is_thinking: reactive[bool] = reactive(False)
    message_count: reactive[int] = reactive(0)

    def compose(self) -> ComposeResult:
        with Horizontal():
            # Sidebar
            with Vertical(id="sidebar"):
                yield Label("CatCode", id="sidebar-title")
                yield Static("─" * 18, classes="session-item")
                for i, session in enumerate(SESSIONS):
                    cls = "session-item session-active" if i == 0 else "session-item"
                    name = session[:16] + ".." if len(session) > 16 else session
                    yield Label(name, classes=cls)

            # Main area
            with Vertical(id="main"):
                # Header
                with Horizontal(id="header-bar"):
                    yield Label("● ", id="status-dot")
                    yield Label("gemini-2.5-flash", id="model-badge")

                # Chat
                with Vertical(id="chat-area"):
                    yield ScrollableContainer(id="messages")

                # Input
                with Vertical(id="input-area"):
                    yield Input(
                        placeholder="Ask CatCode anything...",
                        id="input-box"
                    )
                    yield Label(
                        "Enter to send  •  Ctrl+L to clear  •  Ctrl+C to quit",
                        id="input-hint"
                    )

    def on_mount(self) -> None:
        self.query_one("#input-box", Input).focus()
        self._show_welcome()

    def _show_welcome(self) -> None:
        messages = self.query_one("#messages", ScrollableContainer)
        messages.mount(
            Static(
                "\n\n"
                "  ╭─────────────────────────────╮\n"
                "  │                             │\n"
                "  │    🐱  CatCode  v0.1        │\n"
                "  │                             │\n"
                "  │   Your AI coding agent      │\n"
                "  │   powered by Gemini         │\n"
                "  │                             │\n"
                "  ╰─────────────────────────────╯\n\n"
                "  Type anything to get started...",
                id="welcome"
            )
        )

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return

        event.input.value = ""

        # Remove welcome screen
        try:
            welcome = self.query_one("#welcome", Static)
            await welcome.remove()
        except Exception:
            pass

        # Add user message
        await self._add_message("user", query)

        # Start thinking
        self.is_thinking = True
        self._run_agent(query)

    @work(exclusive=False, thread=True)
    def _run_agent(self, query: str) -> None:
        # Simulate tool calls
        num_tools = random.randint(1, 2)
        for i in range(num_tools):
            time.sleep(0.6)
            tool_call = random.choice(TOOL_CALLS)
            self.call_from_thread(self._show_tool_call, tool_call)

        time.sleep(0.8)

        # Final response
        response = random.choice(FAKE_RESPONSES)
        self.call_from_thread(self._finish_response, response)

    def _show_tool_call(self, tool_call: str) -> None:
        messages = self.query_one("#messages", ScrollableContainer)
        messages.mount(
            Static(f"  ⚙ Tool call: {tool_call}", classes="thinking")
        )
        messages.scroll_end(animate=False)

    def _finish_response(self, response: str) -> None:
        self.is_thinking = False
        self.app.call_later(self._add_message_sync, "assistant", response)

    def _add_message_sync(self, role: str, content: str) -> None:
        asyncio.ensure_future(self._add_message(role, content))

    async def _add_message(self, role: str, content: str) -> None:
        messages = self.query_one("#messages", ScrollableContainer)

        # Remove thinking indicators if assistant
        if role == "assistant":
            for thinking in messages.query(".thinking"):
                await thinking.remove()

        label_cls = "msg-label-user" if role == "user" else "msg-label-assistant"
        label_text = "You" if role == "user" else "CatCode"
        msg_cls = "msg-user" if role == "user" else "msg-assistant"

        await messages.mount(Label(label_text, classes=label_cls))
        await messages.mount(Static(content, classes=msg_cls))
        messages.scroll_end(animate=True)
        self.message_count += 1

    def action_clear(self) -> None:
        messages = self.query_one("#messages", ScrollableContainer)
        messages.remove_children()
        self._show_welcome()

    def action_blur_input(self) -> None:
        self.query_one("#input-box", Input).blur()


if __name__ == "__main__":
    app = CatCodeApp()
    app.run()