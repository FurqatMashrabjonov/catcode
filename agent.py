import os
import json
from pathlib import Path
from dotenv import load_dotenv

from google.genai import types
from managers.provider import ProviderManager
from managers.tool import ToolManager
from managers.prompt import PromptManager
from providers.base_provider import TokenUsage
from cli import Cli

load_dotenv()

MAX_TURNS = 20
KEEP_RECENT = 3
THRESHOLD = 50000

class Agent:
    __api_key = os.getenv('GEMINI_API_KEY')

    def __init__(self, workdir=None):
        self.workdir = Path(workdir or Path.cwd()).resolve()
        self.tool_manager = ToolManager(workdir=self.workdir)
        self.prompt_manager = PromptManager()
        self.provider_manager = ProviderManager()
        self.cli = Cli()

        # Initialize paths relative to workdir
        self.transcript_dir = self.workdir / ".transcripts"
        self.transcript_file = self.transcript_dir / "transcript.jsonl"
        
        self.transcript_dir.mkdir(exist_ok=True, parents=True)
        
        self.contents = []
        self._load_transcript()
        
        self.token_usage = TokenUsage(input=0, output=0, total=0)

        self.provider = self.provider_manager.init_provider(
            type="gemini",
            api_key=self.__api_key,
            model='gemini-3.1-flash-lite-preview'
        )

    def _to_clean_dict(self, content: types.Content) -> dict:
        result = {"role": content.role}
        
        texts = []
        calls = []
        resps = []
        
        for part in content.parts:
            if part.text:
                texts.append(part.text)
            if part.function_call:
                call_data = {"name": part.function_call.name, "args": part.function_call.args}
                if hasattr(part.function_call, 'id') and part.function_call.id:
                    call_data["id"] = part.function_call.id
                calls.append(call_data)
            if part.function_response:
                resp_data = {"name": part.function_response.name, "result": part.function_response.response.get("result") if isinstance(part.function_response.response, dict) else part.function_response.response}
                if hasattr(part.function_response, 'id') and part.function_response.id:
                    resp_data["id"] = part.function_response.id
                resps.append(resp_data)
                
        if texts:
            result["text"] = "\n".join(texts)
        if calls:
            result["function_call"] = calls[0] if len(calls) == 1 else calls
        if resps:
            result["function_response"] = resps[0] if len(resps) == 1 else resps
            
        return result

    def _from_clean_dict(self, data: dict) -> types.Content:
        parts = []
        if "text" in data:
            parts.append(types.Part(text=data["text"]))
            
        if "function_call" in data:
            calls = data["function_call"] if isinstance(data["function_call"], list) else [data["function_call"]]
            for call in calls:
                kwargs = {"name": call["name"], "args": call.get("args", {})}
                if "id" in call: kwargs["id"] = call["id"]
                parts.append(types.Part(function_call=types.FunctionCall(**kwargs)))
                
        if "function_response" in data:
            resps = data["function_response"] if isinstance(data["function_response"], list) else [data["function_response"]]
            for res in resps:
                kwargs = {"name": res["name"], "response": {"result": res.get("result")}}
                if "id" in res: kwargs["id"] = res["id"]
                parts.append(types.Part(function_response=types.FunctionResponse(**kwargs)))
                
        return types.Content(role=data.get("role", "user"), parts=parts)

    def _load_transcript(self):
        """Loads transcript from transcript.jsonl and initializes contents."""
        try:
            if self.transcript_file.exists():
                with open(self.transcript_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            self.contents.append(self._from_clean_dict(data))
        except Exception as e:
            print(f"Error loading transcript: {e}")

    def _append_transcript(self, content: types.Content) -> None:
        try:
            with open(self.transcript_file, "a") as f:
                f.write(json.dumps(self._to_clean_dict(content)) + "\n")
        except Exception as e:
            print(f"Error appending transcript: {e}")

    def ask(self, query: str):
        content = types.Content(
            role="user",
            parts=[types.Part(text=query)]
        )
        self.contents.append(content)
        self._append_transcript(content)
        
        result = self.loop()
        tokens = self._estimate_tokens()
        return result, tokens

    def _estimate_tokens(self) -> TokenUsage:
        return self.token_usage

    def _count_transcript_tokens(self) -> int:
        # Rough offline token estimation (approx 4 chars per token)
        # We check the size of the current conversation history.
        return len(str(self.contents)) // 4

    def loop(self) -> str:
        turns = 0
        tools_since_todo = 0

        while turns < MAX_TURNS:
            turns += 1

            # Layer 1: micro_compact before each LLM call
            self._micro_compact()

            # Layer 2: auto_compact if token estimate exceeds threshold
            current_tokens = self._count_transcript_tokens()
            if current_tokens > THRESHOLD:
                print(f"[auto_compact triggered: {current_tokens} tokens exceed threshold {THRESHOLD}]")
                self._auto_compact()

            # The Nag Reminder: Keep the agent focused if it's drifting
            if tools_since_todo >= 3:
                nag = types.Content(
                    role="user", 
                    parts=[types.Part(text="<reminder>Update your todo list or explicitly continue with the next task.</reminder>")]
                )
                self.contents.append(nag)
                self._append_transcript(nag)
                tools_since_todo = 0

            response = self.provider.generate(
                contents=self.contents,
                tools=self.tool_manager.get_tools(),
                system_instruction=self.prompt_manager.get('agent')
            )
            self.contents.append(response.content)
            self._append_transcript(response.content)

            self.token_usage.input += response.token_usage.input
            self.token_usage.output += response.token_usage.output
            self.token_usage.total += response.token_usage.total

            if not self.provider.has_tool_call(response):
                return response.text

            tool_results = []
            manual_compact = False
            called_todo = False
            
            for call in response.tool_calls:
                if call["name"] == "compact":
                    manual_compact = True
                    result = "Manual compression requested."
                else:
                    result = self.tool_manager.run(call["name"], call["args"])
                
                tool_results.append(
                    self.provider.build_tool_result(
                        call["name"], call["id"], result
                    )
                )

                if call["name"] == "todo":
                    called_todo = True
                    get_emoji = lambda status: (
                        "⏳" if status == "pending" else
                        "⚙️" if status == "in_progress" else
                        "✅" if status == "completed" else
                        "❓"
                    )

                    todo_items = call["args"]["items"] or []
                    todo_str = 'Todo: \n'
                    for todo in todo_items:
                        todo_str += f"{todo['id']}: {todo['text']} {get_emoji(todo['status'])}\n"
                    self.cli.render_body(todo_str)
                elif call["name"] != "compact":
                    self.cli.render_body(f"🪚 {call['name']} : {call['args']}")

                    if result:
                        self.cli.render_body(f"\n{result}\n")

            if called_todo:
                tools_since_todo = 0
            else:
                tools_since_todo += 1

            tool_content = types.Content(role="user", parts=tool_results)
            self.contents.append(tool_content)
            self._append_transcript(tool_content)

            if manual_compact:
                self.cli.render_body("[manual compact]")
                self._auto_compact()

        return "Max turns reached."

    def _auto_compact(self) -> None:
        conversation_text = ""
        for content in self.contents:
            role = content.role
            for part in content.parts:
                if part.text:
                    conversation_text += f"{role}: {part.text}\n"
                elif part.function_call:
                    conversation_text += f"{role}: Called {part.function_call.name} with {part.function_call.args}\n"
                elif part.function_response:
                    conversation_text += f"{role}: Tool result {part.function_response.name}: {part.function_response.response}\n"

        summary_prompt = (
            "Summarize this conversation for continuity. Include: "
            "1) What was accomplished, 2) Current state, 3) Key decisions made. "
            "Be concise but preserve critical details.\n\n" + conversation_text[-50000:]
        )

        response = self.provider.generate(
            contents=[types.Content(role="user", parts=[types.Part(text=summary_prompt)])],
            tools=[],
            system_instruction="You are a context manager. Summarize the conversation."
        )

        self.token_usage.input += response.token_usage.input
        self.token_usage.output += response.token_usage.output
        self.token_usage.total += response.token_usage.total

        summary = response.text

        self.contents = [
            types.Content(role="user", parts=[types.Part(text=f"[Conversation compressed.]\n\n{summary}")]),
            types.Content(role="model", parts=[types.Part(text="Understood. I have the context from the summary. Continuing.")])
        ]
        
        try:
            with open(self.transcript_file, "w") as f:
                for content in self.contents:
                    f.write(json.dumps(self._to_clean_dict(content)) + "\n")
            print(f"[transcript compacted: {self.transcript_file}]")
        except Exception as e:
            print(f"Error rewriting transcript: {e}")

    def _micro_compact(self) -> None:
        tool_results = []
        for i, content in enumerate(self.contents):
            if content.role == "user":
                for j, part in enumerate(content.parts):
                    if part.function_response is not None:
                        # todo toolini umuman compact qilmaymiz
                        if part.function_response.name != "todo":
                            tool_results.append((i, j, part))

        if len(tool_results) <= KEEP_RECENT:
            return

        for i, j, part in tool_results[:-KEEP_RECENT]:
            name = part.function_response.name
            self.contents[i].parts[j] = types.Part(
                function_response=types.FunctionResponse(
                    name=name,
                    response={"result": f"[Previous: used {name}]"}
                )
            )
