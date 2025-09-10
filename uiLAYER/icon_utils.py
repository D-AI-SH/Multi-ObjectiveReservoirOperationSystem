from pathlib import Path
from PyQt6.QtGui import QIcon


_ASSET_DIR = Path(__file__).parent / "assets"


def load_icon(filename: str, fallback_theme: str | None = None) -> QIcon:
    """优先加载本地 assets 目录下的图标；若不存在则回退系统 Theme。"""
    path = _ASSET_DIR / filename
    if path.exists():
        return QIcon(str(path))
    if fallback_theme:
        icon = QIcon.fromTheme(fallback_theme)
        if not icon.isNull():
            return icon
    return QIcon()
