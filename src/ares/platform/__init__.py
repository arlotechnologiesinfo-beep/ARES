"""Platform layer. Windows-only code is imported lazily."""
import sys

from .base import Platform, PlatformError
from .fake import FakePlatform

__all__ = ["Platform", "PlatformError", "FakePlatform", "get_platform"]


def get_platform() -> Platform:
    if sys.platform == "win32":
        from .windows import WindowsPlatform
        return WindowsPlatform()
    return FakePlatform()
