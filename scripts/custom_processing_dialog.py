from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QSlider
from PySide6.QtCore import Qt
import json
import os

CUSTOM_FILE = "custom_settings.json"
DEFAULT_SETTINGS = {
    "eq": 0,
    "width": 0,
    "saturation": 0
}

def save_settings_to_file(settings):
    with open(CUSTOM_FILE, "w") as f:
        json.dump(settings, f, indent=4)

def load_settings_from_file():
    if os.path.exists(CUSTOM_FILE):
        with open(CUSTOM_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_SETTINGS.copy()

class CustomSettingsPopup(QDialog):
    def __init__(self, lang="en"):
        super().__init__()
        self.setWindowTitle("Customize Processing")
        self.setMinimumWidth(400)
        self.lang = lang
        self.settings = load_settings_from_file()

        self.label_eq = QLabel(self.tr("eq_slider"))
        self.eq_layout, self.slider_eq = self._make_slider(self.settings["eq"], lambda val: self.settings.update({"eq": val}))

        self.label_width = QLabel(self.tr("width_slider"))
        self.width_layout, self.slider_width = self._make_slider(self.settings["width"], lambda val: self.settings.update({"width": val}))

        self.label_sat = QLabel(self.tr("sat_slider"))
        self.sat_layout, self.slider_sat = self._make_slider(self.settings["saturation"], lambda val: self.settings.update({"saturation": val}))

        self.button_save = QPushButton("Save")
        self.button_cancel = QPushButton("Cancel")
        self.button_reset = QPushButton("Reset to Default")

        self.button_save.clicked.connect(self.save_and_close)
        self.button_cancel.clicked.connect(self.reject)
        self.button_reset.clicked.connect(self.reset_to_default)

        layout = QVBoxLayout()
        layout.addWidget(self.label_eq)
        layout.addLayout(self.eq_layout)
        layout.addWidget(self.label_width)
        layout.addLayout(self.width_layout)
        layout.addWidget(self.label_sat)
        layout.addLayout(self.sat_layout)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button_reset)
        button_layout.addStretch()
        button_layout.addWidget(self.button_save)
        button_layout.addWidget(self.button_cancel)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def tr(self, key):
        if self.lang == "id":
            return {
                "eq_slider": "Penyesuaian EQ Dasar (±3 dB per langkah)",
                "width_slider": "Kontrol Stereo Width (±1 dB balance)",
                "sat_slider": "Tingkat Saturasi (gain + kompresi)"
            }.get(key, key)
        else:
            return {
                "eq_slider": "Basic EQ Adjustment (±3 dB per step)",
                "width_slider": "Stereo Width Control (±1 dB balance)",
                "sat_slider": "Saturation Amount (gain shift + compression)"
            }.get(key, key)

    def _make_slider(self, value, on_change):
        layout = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(-10, 10)
        slider.setValue(value)

        value_label = QLabel(f"{value:+d}")
        value_label.setFixedWidth(30)

        def update_label(val):
            value_label.setText(f"{val:+d}")
            on_change(val)

        slider.valueChanged.connect(update_label)

        layout.addWidget(slider)
        layout.addWidget(value_label)

        return layout, slider

    def save_and_close(self):
        updated = {
            "eq": self.slider_eq.value(),
            "width": self.slider_width.value(),
            "saturation": self.slider_sat.value()
        }
        save_settings_to_file(updated)
        self.accept()

    def reset_to_default(self):
        self.slider_eq.setValue(DEFAULT_SETTINGS["eq"])
        self.slider_width.setValue(DEFAULT_SETTINGS["width"])
        self.slider_sat.setValue(DEFAULT_SETTINGS["saturation"])
