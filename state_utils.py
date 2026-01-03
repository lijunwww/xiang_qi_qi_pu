import os
import json

APP_STATE_DIR = os.path.join(os.path.expanduser("~"), ".xiangqi_app")
RECENT_JSON = os.path.join(APP_STATE_DIR, "recent_games.json")
BOOKMARK_JSON = os.path.join(APP_STATE_DIR, "bookmarks.json")
SETTINGS_JSON = os.path.join(APP_STATE_DIR, "settings.json")


def ensure_state_dir():
    os.makedirs(APP_STATE_DIR, exist_ok=True)


def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def write_json(path, obj):
    try:
        ensure_state_dir()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
