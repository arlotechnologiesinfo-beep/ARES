"""In-memory Platform for tests and non-Windows hosts."""
from __future__ import annotations

import os
import shutil
import tempfile
import uuid

from .base import Platform, PlatformError


class FakePlatform(Platform):
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.volume, self.muted, self.brightness, self.theme = 50, False, 70, "dark"
        self.desktop_shown = False
        self.active_window = "Untitled - Notepad"
        self.known_apps = {"notepad", "chrome", "calculator", "edge", "explorer"}
        self.reminders: list[tuple[int, str]] = []
        self.notifications: list[tuple[str, str]] = []
        self.bin_dir = tempfile.mkdtemp(prefix="ares-fakebin-")
        self._bin: list[tuple[str, str]] = []  # (original path, path inside bin)

    def _rec(self, *call) -> None:
        self.calls.append(call)

    def open_app(self, name):
        self._rec("open_app", name)
        return name.strip().lower() in self.known_apps

    def open_url(self, url):
        self._rec("open_url", url)

    def open_folder(self, path):
        self._rec("open_folder", path)

    def get_volume(self):
        return self.volume

    def set_volume(self, level):
        self._rec("set_volume", level)
        self.volume = max(0, min(100, int(level)))

    def get_mute(self):
        return self.muted

    def set_mute(self, muted):
        self._rec("set_mute", muted)
        self.muted = bool(muted)

    def get_brightness(self):
        return self.brightness

    def set_brightness(self, level):
        self._rec("set_brightness", level)
        self.brightness = max(0, min(100, int(level)))

    def get_theme(self):
        return self.theme

    def set_theme(self, mode):
        self._rec("set_theme", mode)
        self.theme = mode

    def show_desktop(self):
        self._rec("show_desktop")
        self.desktop_shown = not self.desktop_shown

    def close_active_window(self):
        self._rec("close_active_window")
        return self.active_window

    def screenshot(self, path):
        self._rec("screenshot", path)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            f.write(b"\x89PNG fake")
        return path

    def recycle(self, paths):
        self._rec("recycle", list(paths))
        for p in paths:
            if not os.path.exists(p):
                raise PlatformError(f"{os.path.basename(p)} does not exist")
        for p in paths:
            dest = os.path.join(self.bin_dir, uuid.uuid4().hex + "_" + os.path.basename(p))
            shutil.move(p, dest)
            self._bin.append((p, dest))

    def restore_from_recycle(self, original_paths):
        self._rec("restore_from_recycle", list(original_paths))
        count = 0
        for p in original_paths:
            for i in range(len(self._bin) - 1, -1, -1):
                orig, inbin = self._bin[i]
                if orig == p:
                    os.makedirs(os.path.dirname(orig), exist_ok=True)
                    shutil.move(inbin, orig)
                    del self._bin[i]
                    count += 1
                    break
        return count

    def notify(self, title, message):
        self._rec("notify", title, message)
        self.notifications.append((title, message))

    def schedule_reminder(self, minutes, message):
        self._rec("schedule_reminder", minutes, message)
        self.reminders.append((minutes, message))
