from abc import ABC, abstractmethod

from app.domain import Candidate


class MarketProvider(ABC):
    """Adapter contract for permitted bookmaker/data-provider integrations."""

    name: str

    @abstractmethod
    async def fetch_candidates(self) -> list[Candidate]:
        raise NotImplementedError


class ResultProvider(ABC):
    """Adapter contract for permitted results/statistics integrations."""

    name: str

    @abstractmethod
    async def fetch_result(self, event_id: str) -> dict | None:
        raise NotImplementedError
