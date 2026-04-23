from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict

from ..contracts import BlockCandidate


class CandidateStore(ABC):
    @abstractmethod
    def save(self, block_id: str, candidates: list[BlockCandidate]) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(self, block_id: str) -> list[BlockCandidate]:
        raise NotImplementedError


class InMemoryCandidateStore(CandidateStore):
    def __init__(self):
        self._store: dict[str, list[BlockCandidate]] = defaultdict(list)

    def save(self, block_id: str, candidates: list[BlockCandidate]) -> None:
        self._store[block_id].extend(candidates)

    def get(self, block_id: str) -> list[BlockCandidate]:
        return list(self._store.get(block_id, []))
