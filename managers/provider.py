from enum import Enum
from providers.base_provider import BaseProvider

class ProviderType(Enum):
    GEMINI = "gemini"

class ProviderManager:
    _providers: dict[str, BaseProvider] = {}

    def init_provider(self, type: str, **kwargs) -> BaseProvider:
        if type in self._providers:
            return self._providers[type]

        provider = self._create(type, **kwargs)
        self._providers[type] = provider
        return provider

    def get(self, type: str) -> BaseProvider:
        if type not in self._providers:
            raise ValueError(f"Provider '{type}' not initialized. Call init_provider first.")
        return self._providers[type]

    def _create(self, type: str, **kwargs) -> BaseProvider:
        match type:
            case "gemini":
                from providers.gemini import GeminiProvider
                return GeminiProvider(**kwargs)
            case _:
                raise ValueError(f"Unknown provider: {type}")