"""Configuración persistente e historial de DVDY Studio."""
import json
import os
import threading
import time

APP_NAME = "DVDY Studio"
APP_VERSION = "2.0.1"

CONFIG_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "DVDY Studio")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.json")
ARCHIVE_FILE = os.path.join(CONFIG_DIR, "download_archive.txt")


def _default_dir(name):
    path = os.path.join(os.path.expanduser("~"), name)
    return path if os.path.isdir(path) else os.path.expanduser("~")


DEFAULTS = {
    "output_dir": _default_dir("Downloads"),
    "music_dir": _default_dir("Music"),
    "filename_template": "%(title)s.%(ext)s",
    "playlist_template": "%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s",
    "max_concurrent": 2,
    "concurrent_fragments": 4,
    "retries": 10,
    "rate_limit": "",
    "proxy": "",
    "geo_bypass": True,
    "restrict_filenames": False,
    "cookies_browser": "",
    "cookies_file": "",
    "ffmpeg_path": "",
    "embed_metadata": True,
    "embed_thumbnail": True,
    "default_video_quality": "1080",
    "default_container": "mp4",
    "default_audio_format": "mp3",
    "default_audio_quality": "320K",
    "use_archive": False,
    "clipboard_monitor": False,
    "notify_on_finish": True,
    "theme": "dark",
    "accent": "#7c5cff",
    "window_geometry": None,
    "ui_mode": "advanced",
    "skip_component_check": "",
}


class Config:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                self._data.update(json.load(f))
        except (OSError, ValueError):
            pass

    def save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        tmp = CONFIG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, CONFIG_FILE)

    def get(self, key, default=None):
        return self._data.get(key, DEFAULTS.get(key, default))

    def set(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        self.set(key, value)


class History:
    MAX = 2000

    def __init__(self):
        self._lock = threading.Lock()
        self.items = []
        try:
            with open(HISTORY_FILE, encoding="utf-8") as f:
                self.items = json.load(f)
        except (OSError, ValueError):
            self.items = []

    def add(self, title, kind, path, url=""):
        with self._lock:
            self.items.insert(0, {
                "date": time.strftime("%Y-%m-%d %H:%M"),
                "title": title,
                "kind": kind,
                "path": path or "",
                "url": url or "",
            })
            del self.items[self.MAX:]
            self._save()

    def remove(self, index):
        with self._lock:
            if 0 <= index < len(self.items):
                del self.items[index]
                self._save()

    def clear(self):
        with self._lock:
            self.items = []
            self._save()

    def _save(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.items, f, indent=1, ensure_ascii=False)


cfg = Config()
history = History()
