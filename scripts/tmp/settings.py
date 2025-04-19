import json, os

DEFAULT_SETTINGS = {
    "language": "id",
    "theme": "light"
}

SETTINGS_PATH = "settings.json"

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULT_SETTINGS)
    with open(SETTINGS_PATH, 'r') as f:
        return json.load(f)

def save_settings(settings):
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=4)
