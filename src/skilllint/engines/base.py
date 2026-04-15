from __future__ import annotations

from abc import ABC, abstractmethod

from skilllint.core.workspace import PreparedWorkspace
from skilllint.models import Finding


class Engine(ABC):
    """所有检测引擎的最小接口。

    引擎只接收 PreparedWorkspace，返回统一 Finding 列表；
    不负责 summary、相关性、报告渲染等后处理工作。
    """
    name: str

    @abstractmethod
    def run(self, workspace: PreparedWorkspace) -> list[Finding]:
        raise NotImplementedError
