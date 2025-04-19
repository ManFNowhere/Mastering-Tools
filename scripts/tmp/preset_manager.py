import json

def save_preset(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def load_preset(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)