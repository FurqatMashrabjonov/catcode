from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Any
import math

@dataclass
class TokenUsage:
    input: int
    output: int
    total: int

    def _human_readable(self, value: int) -> str:
        if value < 1000:
            return str(value)

        units = ['', 'K', 'M', 'B', 'T']
        index = int(math.floor(math.log10(value) / 3))
        scaled_value = value / (1000 ** index)

        return f"{scaled_value:g}{units[index]}"

    @property
    def input_readable(self) -> str:
        return self._human_readable(self.input)

    @property
    def output_readable(self) -> str:
        return self._human_readable(self.output)

    @property
    def total_readable(self) -> str:
        return self._human_readable(self.total)

@dataclass
class AgentResponse:
    text: str
    tool_calls: list[dict]
    content: Any
    token_usage: TokenUsage

class BaseProvider(ABC):
    pass

    @abstractmethod
    def generate(self, contents: List, tools: List, system_instruction: str) -> AgentResponse:
        pass


    @abstractmethod
    def build_tool_result(self, tool_name: str, tool_id: str, result: str) -> object:
        """Tool natijasini provider formatiga o'giradi"""
        ...

    @abstractmethod
    def build_user_message(self, text: str) -> object:
        """User message ni provider formatiga o'giradi"""
        ...

    @abstractmethod
    def has_tool_call(self, response: AgentResponse) -> bool:
        """Tool call bormi?"""
        ...