"""Explicit LangGraph tool construction."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExplicitTool:
    """Small explicit tool descriptor used by workflow nodes.

    This intentionally avoids decorator-based registration.
    """

    name: str
    description: str
    func: Callable[..., Any]

    def invoke(self, **kwargs: Any) -> Any:
        return self.func(**kwargs)


def make_tool(name: str, description: str, func: Callable[..., Any]) -> ExplicitTool:
    return ExplicitTool(name=name, description=description, func=func)
