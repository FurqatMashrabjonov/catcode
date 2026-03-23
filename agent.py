from google import genai
from google.genai import types
from tool_manager import Tool
from pathlib import Path
from prompt_manager import PromptManager

MAX_TURNS = 20
KEEP_RECENT = 3

class Agent:
    __api_key = ''

    def __init__(self):
        self.__workdir = Path('/Users/furqat/apps/emaydonlaravel')
        self.__tool_manager = Tool(workdir=self.__workdir)
        self.__client = genai.Client(api_key=self.__api_key)
        self.__gemini_tools = [
            types.Tool(
                function_declarations=self.__tool_manager.get_tools(),
                google_search=types.GoogleSearch(),
                url_context=types.UrlContext()
            )
        ]
        self.prompt_manager = PromptManager()
        self.__config = types.GenerateContentConfig(
            system_instruction=[self.prompt_manager.get('agent')],
            tools=self.__gemini_tools,
        )

        self.contents = []
        self.total_token_usage = 0

    def ask(self, query: str):
        self.contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=query)]
            )
        )
        result = self.loop()
        tokens = self._estimate_tokens()
        return result, tokens

    def _estimate_tokens(self) -> int:
        return len(str(self.contents)) // 4

    def loop(self) -> str:
        turns = 0

        while turns < MAX_TURNS:
            turns += 1

            # Layer 1 — har turn boshida
            self._micro_compact()

            response = self.__client.models.generate_content(
                model="gemini-3.1-flash-lite-preview",
                contents=self.contents,
                config=self.__config,
            )

            candidate = response.candidates[0]
            self.contents.append(candidate.content)

            tool_calls = [
                p for p in candidate.content.parts
                if p.function_call is not None
            ]

            if not tool_calls:
                return " ".join(
                    p.text for p in candidate.content.parts
                    if hasattr(p, "text") and p.text
                )

            tool_results = []
            for part in tool_calls:
                fn = part.function_call
                print(f"Tool call: {fn.name}({dict(fn.args)})")
                result = self.__tool_manager.run(fn.name, dict(fn.args))
                tool_results.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fn.name,
                            response={"result": result}
                        )
                    )
                )

            self.contents.append(
                types.Content(role="user", parts=tool_results)
            )

        return "Max turns reached."

    def _micro_compact(self) -> None:
        # Gemini da tool result = role "user", function_response part
        tool_results = []
        for i, content in enumerate(self.contents):
            if content.role == "user":
                for j, part in enumerate(content.parts):
                    if part.function_response is not None:
                        tool_results.append((i, j, part))

        # 3 dan kam bo'lsa — hech narsa qilma
        if len(tool_results) <= KEEP_RECENT:
            return

        # Eski result larni replace
        for i, j, part in tool_results[:-KEEP_RECENT]:
            name = part.function_response.name
            self.contents[i].parts[j] = types.Part(
                function_response=types.FunctionResponse(
                    name=name,
                    response={"result": f"[Previous: used {name}]"}
                )
            )