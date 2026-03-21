from google import genai
from google.genai import types
from tool_manager import Tool
from pathlib import Path


class Agent:
    __api_key = 'AIzaSyD4ZduhCRz5mikQskczvDce6ILun3Ndkrw'

    def __init__(self):
        self.__workdir = Path('/Users/furqat/apps/emaydonlaravel')
        self.__tool_manager = Tool(workdir=self.__workdir)
        self.__client = genai.Client(api_key=self.__api_key)
        self.__gemini_tools = types.Tool(
            function_declarations=self.__tool_manager.get_tools()
        )
        self.__config = types.GenerateContentConfig(
            tools=[self.__gemini_tools]
        )
        self.contents = []

    def ask(self, query: str):
        return self.loop(query)

    def loop(self, query: str) -> str:
        # User message qo'sh
        self.contents.append(
            types.Content(
                role="user",
                parts=[types.Part(text=query)]
            )
        )

        while True:
            response = self.__client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=self.contents,
                config=self.__config,
            )

            candidate = response.candidates[0]
            self.contents.append(candidate.content)

            # Tool call bormi?
            tool_calls = [
                part for part in candidate.content.parts
                if part.function_call is not None
            ]

            # Tool call yo'q — final answer
            if not tool_calls:
                return candidate.content.parts[0].text

            # Tool call bor — ishga tushir
            tool_results = []
            for part in tool_calls:
                fn = part.function_call
                print(f"Tool call: {fn.name}({dict(fn.args)})")

                result = self.__tool_manager.run(
                    name=fn.name,
                    args=dict(fn.args)
                )

                tool_results.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=fn.name,
                            response={"result": result}
                        )
                    )
                )

            # Tool natijalarini contents ga qo'sh
            self.contents.append(
                types.Content(
                    role="user",
                    parts=tool_results
                )
            )