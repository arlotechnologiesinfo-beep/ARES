"""SQLite store: action log, undo stack, learned phrases, memory."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Any, Optional

from .contracts import ToolCall, UndoAction

_SCHEMA = """
CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY, ts REAL, phrase TEXT, tool TEXT, args TEXT, ok INTEGER, message TEXT);
CREATE TABLE IF NOT EXISTS undo(id INTEGER PRIMARY KEY, tool TEXT, args TEXT, description TEXT);
CREATE TABLE IF NOT EXISTS learned(phrase TEXT PRIMARY KEY, tool TEXT, args TEXT);
CREATE TABLE IF NOT EXISTS memory(key TEXT PRIMARY KEY, value TEXT);
"""


class Store:
    def __init__(self, db_path: str = ":memory:") -> None:
        self._lock = threading.RLock()
        self._db = sqlite3.connect(db_path, check_same_thread=False)
        self._db.executescript(_SCHEMA)

    def _run(self, sql: str, params: tuple = ()) -> list:
        with self._lock:
            rows = self._db.execute(sql, params).fetchall()
            self._db.commit()
            return rows

    # action log
    def log_action(self, phrase: str, tool: str, args: dict, ok: bool, message: str) -> None:
        self._run("INSERT INTO actions(ts,phrase,tool,args,ok,message) VALUES(?,?,?,?,?,?)",
                  (time.time(), phrase, tool, json.dumps(args, default=str), int(ok), message))

    def recent_actions(self, n: int = 10) -> list[dict[str, Any]]:
        rows = self._run("SELECT ts,phrase,tool,args,ok,message FROM actions ORDER BY id DESC LIMIT ?", (n,))
        return [{"ts": r[0], "phrase": r[1], "tool": r[2], "args": json.loads(r[3]), "ok": bool(r[4]),
                 "message": r[5]} for r in rows]

    # undo stack
    def push_undo(self, undo: UndoAction) -> None:
        self._run("INSERT INTO undo(tool,args,description) VALUES(?,?,?)",
                  (undo.tool, json.dumps(undo.args, default=str), undo.description))

    def pop_undo(self) -> Optional[UndoAction]:
        with self._lock:
            rows = self._db.execute("SELECT id,tool,args,description FROM undo ORDER BY id DESC LIMIT 1").fetchall()
            if not rows:
                return None
            self._db.execute("DELETE FROM undo WHERE id=?", (rows[0][0],))
            self._db.commit()
        return UndoAction(rows[0][1], json.loads(rows[0][2]), rows[0][3])

    # learned phrases
    def learn(self, phrase: str, tool: str, args: dict) -> None:
        self._run("INSERT OR REPLACE INTO learned(phrase,tool,args) VALUES(?,?,?)",
                  (phrase, tool, json.dumps(args, default=str)))

    def lookup(self, phrase: str) -> Optional[ToolCall]:
        rows = self._run("SELECT tool,args FROM learned WHERE phrase=?", (phrase,))
        return ToolCall(rows[0][0], json.loads(rows[0][1]), source="learned") if rows else None

    def forget(self, phrase: str) -> None:
        self._run("DELETE FROM learned WHERE phrase=?", (phrase,))

    # memory
    def set_memory(self, key: str, value: Any) -> None:
        self._run("INSERT OR REPLACE INTO memory(key,value) VALUES(?,?)", (key, json.dumps(value)))

    def get_memory(self, key: str, default: Any = None) -> Any:
        rows = self._run("SELECT value FROM memory WHERE key=?", (key,))
        return json.loads(rows[0][0]) if rows else default

    def all_memory(self) -> dict[str, Any]:
        return {k: json.loads(v) for k, v in self._run("SELECT key,value FROM memory")}

    def delete_memory(self, key: str) -> None:
        self._run("DELETE FROM memory WHERE key=?", (key,))
