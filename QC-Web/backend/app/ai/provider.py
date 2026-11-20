"""Abstract Base Class for AI Test Generation Providers."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List


class AIProvider(ABC):
    """Abstract interface for AI test generation providers."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider API keys and dependencies are configured."""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return provider name (e.g., 'gemini', 'openai')."""
        pass

    @abstractmethod
    def generate_test_cases(self, app_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate structured test cases from discovered application context."""
        pass
