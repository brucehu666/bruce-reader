import json
from typing import Any, Dict
from config import (
    CONFIG_FILE, DEFAULT_FONT_FAMILY, DEFAULT_FONT_SIZE,
    DEFAULT_LINE_SPACING, DEFAULT_TTS_RATE, DEFAULT_TTS_VOLUME,
    COLOR_THEMES
)


class SettingsManager:
    def __init__(self):
        self.settings: Dict[str, Any] = self._load_default_settings()
        self._load_settings()

    def _load_default_settings(self) -> Dict[str, Any]:
        return {
            "font_family": DEFAULT_FONT_FAMILY,
            "font_size": DEFAULT_FONT_SIZE,
            "line_spacing": DEFAULT_LINE_SPACING,
            "color_theme": "default",
            "tts_rate": DEFAULT_TTS_RATE,
            "tts_volume": DEFAULT_TTS_VOLUME,
            "tts_voice": 0,
            "window_geometry": None,
            "window_state": None
        }

    def _load_settings(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    saved = json.load(f)
                    self.settings.update(saved)
        except Exception:
            pass

    def save_settings(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        self.settings[key] = value
        self.save_settings()

    def get_theme_colors(self) -> Dict[str, str]:
        theme = self.get("color_theme", "default")
        return COLOR_THEMES.get(theme, COLOR_THEMES["default"])
