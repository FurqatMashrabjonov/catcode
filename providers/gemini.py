import os
from types import NoneType
from typing import List

from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai.types import RetrievalConfig, ToolConfig

load_dotenv()

from providers.base_provider import BaseProvider, AgentResponse, TokenUsage


class GeminiProvider(BaseProvider):
    def __init__(self, api_key, model):
        self.__api_key = api_key
        self.__model = model
        self.__client = genai.Client(api_key=self.__api_key)



    def generate(self, contents: List, tools: List, system_instruction: str) -> AgentResponse:
        #error handling qo'shish kerak

        response = self.__client.models.generate_content(
            model=self.__model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                tools=[
                    types.Tool(
                        function_declarations=tools,
                        google_search=types.GoogleSearch(),
                        url_context=types.UrlContext()
                    )
                ],
            tool_config=ToolConfig(
                include_server_side_tool_invocations=True
            )
            ),
        )

        candidate = response.candidates[0]
        # tool_calls = [
        #     {"name": p.tool_call.name,
        #      "args": dict(p.tool_call.args),
        #      "id": p.tool_call.id if hasattr(p.tool_call, 'id') else p.tool_call.name}
        #     for p in candidate.content.parts
        #     if p.tool_call is not None
        # ]

        tool_calls = []

        for part in candidate.content.parts:
            if part.function_call is not None:
                tool_calls.append({
                    "id": part.function_call.id,
                    "args": dict(part.function_call.args),
                    "name": part.function_call.name
                })

        text = " ".join(p.text for p in candidate.content.parts if hasattr(p, "text") and p.text)

        return AgentResponse(
            text=text,
            tool_calls=tool_calls,
            content=candidate.content,
            token_usage= TokenUsage(
                input=response.usage_metadata.candidates_token_count,
                output=response.usage_metadata.prompt_token_count,
                total=response.usage_metadata.total_token_count
            )
        )

    def build_tool_result(self, tool_name: str, tool_id: str, result: str) -> object:
        return types.Part(
            function_response=types.FunctionResponse(
                name=tool_name,
                response={"result": result}
            )
        )

    def build_user_message(self, text: str) -> object:
        return types.Content(
            role="user",
            parts=[types.Part(text=text)]
        )

    def has_tool_call(self, response: AgentResponse) -> bool:
        return len(response.tool_calls) > 0

