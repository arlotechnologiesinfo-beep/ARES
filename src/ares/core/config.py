"""ARES configuration, stored as JSON in data_dir/config.json."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from .contracts import Permission

GROUPS = [p.value for p in Permission if p is not Permission.NONE]


def _home() -> str:
    return os.path.expanduser("~")


def default_roots() -> list[str]:
    return [os.path.join(_home(), d) for d in ("Downloads", "Documents", "Desktop")]


def default_data_dir() -> str:
    return os.path.join(_home(), ".ares")


def default_permissions() -> dict[str, bool]:
    return {g: False for g in GROUPS}


@dataclass
class Config:
    allowed_roots: list[str] = field(default_factory=default_roots)
    permissions: dict[str, bool] = field(default_factory=default_permissions)
    data_dir: str = field(default_factory=default_data_dir)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:4b"
    max_files_per_action: int = 10

    def is_allowed(self, permission) -> bool:
        value = getattr(permission, "value", permission)
        if value == Permission.NONE.value:
            return True
        return bool(self.permissions.get(value, False))

    def set_permission(self, group: str, allowed: bool) -> None:
        self.permissions[group] = allowed

    @property
    def path(self) -> str:
        return os.path.join(self.data_dir, "config.json")

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        cfg = cls()
        path = path or cfg.path
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, ValueError):
            if path != cfg.path:
                cfg.data_dir = os.path.dirname(os.path.abspath(path))
            return cfg
        for key, val in raw.items():
            if key == "permissions" and isinstance(val, dict):
                cfg.permissions.update({k: bool(v) for k, v in val.items()})
            elif hasattr(cfg, key) and key != "permissions":
                setattr(cfg, key, val)
        if "data_dir" not in raw:
            cfg.data_dir = os.path.dirname(os.path.abspath(path))
        return cfg

    def save(self, path: Optional[str] = None) -> str:
        path = path or self.path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.__dict__, f, indent=2)
        return path
