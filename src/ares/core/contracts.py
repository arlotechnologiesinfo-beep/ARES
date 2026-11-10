"""Shared contracts for ARES. Every module builds on these types.

Do not change signatures here without updating all of core, tools, voice and ui.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Protocol


class Risk(str, Enum):
    READ_ONLY = "read_only"              # run immediately
    AUTO_REVERSIBLE = "auto_reversible"  # run immediately, push undo
    REVERSIBLE = "reversible"            # one confirmation, push undo
    DESTRUCTIVE = "destructive"          # preview + explicit confirmation
    FORBIDDEN = "forbidden"              # never run


class Permission(str, Enum):
    NONE = "none"          # always allowed (clock, help)
    FILES = "files"
    APPS = "apps"
    BROWSER = "browser"
    SYSTEM = "system"
    MICROPHONE = "microphone"


class State(str, Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    WORKING = "working"
    SPEAKING = "speaking"


@dataclass
class UndoAction:
    """How to revert an action: call tool `tool` with `args` (bypasses confirmation)."""
    tool: str
    args: dict[str, Any]
    description: str = ""


@dataclass
class ToolResult:
    ok: bool
    message: str                       # short, speakable sentence
    data: Any = None
    undo: Optional[UndoAction] = None


@dataclass
class ToolContext:
    platform: Any                      # ares.platform.base.Platform
    config: Any                        # ares.core.config.Config (allowed_roots, permissions, ...)
    store: Any = None                  # ares.core.store.Store


# handler(ctx, **args) -> ToolResult
Handler = Callable[..., ToolResult]
# preview(ctx, args) -> plain-language sentence of what will happen
Preview = Callable[[ToolContext, dict[str, Any]], str]


@dataclass
class Tool:
    name: str
    description: str
    params: dict[str, Any]             # JSON-schema "properties" dict; see `required`
    risk: Risk
    permission: Permission
    handler: Handler
    required: list[str] = field(default_factory=list)
    preview: Optional[Preview] = None
    path_params: list[str] = field(default_factory=list)  # arg names holding file paths (str or list[str]);
                                                          # safety checks these against allowed roots
    hidden: bool = False               # undo-only helper tools: never routed to or shown to the model


class Registry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def all(self, include_hidden: bool = False) -> list[Tool]:
        return [t for t in self._tools.values() if include_hidden or not t.hidden]

    def schemas(self) -> list[dict[str, Any]]:
        """Tool descriptions for the language model (hidden and forbidden tools excluded)."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": {"type": "object", "properties": t.params, "required": t.required},
            }
            for t in self.all()
            if t.risk is not Risk.FORBIDDEN
        ]


@dataclass
class ToolCall:
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    source: str = "rules"              # "rules" | "learned" | "model"


@dataclass
class Reply:
    text: str                          # what to show / speak
    ok: bool = True
    needs_confirmation: bool = False   # True: next handle_text() should be yes / no
    call: Optional[ToolCall] = None


class EngineProtocol(Protocol):
    """What voice, ui and cli may rely on. Implemented by ares.core.engine.Engine."""

    def handle_text(self, text: str) -> Reply: ...
    def stop(self) -> Reply: ...
    def subscribe(self, callback: Callable[[State, str], None]) -> None:
        """callback(state, detail) is called on every state change; detail may be ''."""
        ...
    @property
    def pending_prompt(self) -> Optional[str]: ...
