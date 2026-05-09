import os
import sys
from pathlib import Path

APP_NAME = "PCReader"
APP_VERSION = "1.0.0"

def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent.absolute()

BASE_DIR = get_base_dir()

DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
CONFIG_FILE = DATA_DIR / "config.json"
RECENT_FILES_FILE = DATA_DIR / "recent_files.json"
BOOKMARKS_FILE = DATA_DIR / "bookmarks.json"

for directory in [DATA_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

ENCODINGS = ["utf-8", "gbk", "gb2312", "gb18030", "utf-16", "ansi"]

MAX_RECENT_FILES = 15

DEFAULT_FONT_FAMILY = "Microsoft YaHei"
DEFAULT_FONT_SIZE = 14
MIN_FONT_SIZE = 8
MAX_FONT_SIZE = 32
DEFAULT_LINE_SPACING = 1.5

COLOR_THEMES = {
    "default": {
        "background": "#FFFFFF",
        "foreground": "#000000"
    },
    "sepia": {
        "background": "#F4ECD8",
        "foreground": "#5C4B37"
    },
    "night": {
        "background": "#1E1E1E",
        "foreground": "#D4D4D4"
    },
    "green": {
        "background": "#CCE8CF",
        "foreground": "#2E5B33"
    }
}

DEFAULT_TTS_RATE = 1.0
MIN_TTS_RATE = 0.5
MAX_TTS_RATE = 2.0
TTS_RATE_STEP = 0.1
DEFAULT_TTS_VOLUME = 0.8

CHUNK_SIZE = 100 * 1024
MAX_SINGLE_LOAD = 5 * 1024 * 1024