from __future__ import annotations

from abc import ABC, abstractmethod

from skilllint.core.workspace import PreparedWorkspace
from skilllint.models import Finding


class Engine(ABC):
    name: str

    @abstractmethod
    def run(self, workspace: PreparedWorkspace) -> list[Finding]:
        raise NotImplementedError
