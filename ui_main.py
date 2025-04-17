from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout,
    QCheckBox, QProgressBar, QFileDialog, QComboBox
)
from PySide6.QtCore import Qt, QTimer, QMetaObject, Slot
import os
import threading
import json
import soundfile as sf
import numpy as np
from scripts.mastering import master_audio
from scripts.utils import analyze_loudness, get_loudness_hint_for_lang
from scripts.presets import platform_presets
from scripts.audio_player_widget import AudioPlayerWidget
from scripts.recommender import recommend_gain

class MasteringApp(QWidget):
    def __init__(self):
        super().__init__()
        print("🔧 Initializing MasteringApp GUI...")
        self.setWindowTitle("Mastering Tool - Secret Silence")
        self.setMinimumWidth(700)
        self.load_settings()
        self.load_language()
        self.setup_ui()
        self.original_audio = None
        self.mastered_audio = None
        self.current_platform = "Spotify"

    def load_settings(self):
        if os.path.exists("settings.json"):
            with open("settings.json", "r", encoding="utf-8") as f:
                self.settings = json.load(f)
        else:
            self.settings = {"lang": "en"}
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.settings, f)

    def save_settings(self):
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(self.settings, f)

    def load_language(self):
        print("🌐 Loading language JSON...")
        with open("lang.json", "r", encoding="utf-8") as f:
            self.lang_data = json.load(f)
        self.current_lang = self.settings.get("lang", "en")

    def tr(self, key, **kwargs):
        text = self.lang_data.get(self.current_lang, {}).get(key, key)
        return text.format(**kwargs) if kwargs else text

    def setup_ui(self):
        self.label_select = QLabel(self.tr("select_file"))
        self.entry_file = QLineEdit()
        self.entry_file.setReadOnly(True)
        self.entry_file.textChanged.connect(self.reset_ui)
        self.button_browse = QPushButton(self.tr("browse"))
        self.button_browse.clicked.connect(self.browse_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.label_select)
        file_layout.addWidget(self.entry_file)
        file_layout.addWidget(self.button_browse)

        self.label_gain = QLabel(self.tr("gain_label"))
        self.entry_gain = QLineEdit("0.0")
        self.entry_gain.textChanged.connect(self.reset_ui)

        self.cb_eq = QCheckBox(self.tr("eq"))
        self.cb_width = QCheckBox(self.tr("width"))
        self.cb_sat = QCheckBox(self.tr("saturation"))
        for cb in [self.cb_eq, self.cb_width, self.cb_sat]:
            cb.stateChanged.connect(self.reset_ui)

        self.platform_label = QLabel(self.tr("platform"))
        self.platform_selector = QComboBox()
        self.platform_selector.addItems(platform_presets.keys())
        self.platform_selector.setCurrentText("Spotify")
        self.platform_selector.currentTextChanged.connect(lambda p: setattr(self, "current_platform", p))

        
        self.label_gain = QLabel(self.tr("gain_label"))
        self.entry_gain = QLineEdit("0.0")
        self.entry_gain.textChanged.connect(self.reset_ui)
        self.button_recommend_gain = QPushButton(self.tr("recommend_gain"))
        self.button_recommend_gain.clicked.connect(self.apply_recommended_gain)

        options_layout = QHBoxLayout()
        options_layout.addWidget(self.label_gain)
        options_layout.addWidget(self.entry_gain)
        options_layout.addWidget(self.button_recommend_gain)
        options_layout.addWidget(self.cb_eq)
        options_layout.addWidget(self.cb_width)
        options_layout.addWidget(self.cb_sat)
        options_layout.addWidget(self.platform_label)
        options_layout.addWidget(self.platform_selector)

        self.button_process = QPushButton(self.tr("start"))
        self.button_process.clicked.connect(self.process_audio)

        self.progress = QProgressBar()
        self.progress.hide()

        self.label_status = QLabel("")
        self.label_preview = QLabel(self.tr("preview"))
        self.label_preview.hide()
        self.hint_label = QLabel("")
        self.hint_label.setWordWrap(True)
        self.hint_label.hide()

        self.preview_section = QWidget()
        self.preview_layout = QVBoxLayout()
        self.preview_section.setLayout(self.preview_layout)
        self.preview_section.hide()

        self.original_preview = QWidget()
        self.original_preview.setLayout(QVBoxLayout())
        self.mastered_preview = QWidget()
        self.mastered_preview.setLayout(QVBoxLayout())
        self.preview_layout.addWidget(QLabel(self.tr("original")))
        self.preview_layout.addWidget(self.original_preview)
        self.preview_layout.addWidget(QLabel(self.tr("mastered")))
        self.preview_layout.addWidget(self.mastered_preview)

        self.button_save = QPushButton(self.tr("save"))
        self.button_save.clicked.connect(self.save_output)
        self.button_save.hide()

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["English", "Bahasa Indonesia"])
        self.combo_lang.setCurrentIndex(1 if self.current_lang == "id" else 0)
        self.combo_lang.currentIndexChanged.connect(self.change_language)

        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        lang_layout.addWidget(QLabel(self.tr("language")))
        lang_layout.addWidget(self.combo_lang)

        layout = QVBoxLayout()
        layout.addLayout(file_layout)
        layout.addLayout(options_layout)
        layout.addWidget(self.button_process)
        layout.addWidget(self.progress)
        layout.addWidget(self.label_status)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.label_preview)
        layout.addWidget(self.preview_section)
        layout.addWidget(self.button_save)
        layout.addLayout(lang_layout)

        self.setLayout(layout)


    def auto_gain(self):
        file_path = self.entry_file.text()
        if not os.path.isfile(file_path):
            self.label_status.setText(self.tr("no_file"))
            return

        try:
            result = recommend_gain(file_path, self.current_platform)
            gain = result["recommended_gain"]
            self.entry_gain.setText(f"{gain:.2f}")
            self.label_status.setText(self.tr("gain_recommended", 
                                              current=f"{result['current_lufs']:.2f}", 
                                              target=f"{result['target_lufs']:.2f}"))
        except Exception as e:
            print("❌ Auto Gain Error:", e)
            self.label_status.setText(self.tr("gain_error"))

    
    def apply_recommended_gain(self):
        file_path = self.entry_file.text()
        if not os.path.isfile(file_path):
            self.label_status.setText("Invalid file.")
            return

        result = recommend_gain(file_path, self.current_platform)
        self.entry_gain.setText(f"{result['recommended_gain']:.2f}")
        self.label_status.setText(
            self.tr("gain_recommended", current=f"{result['current_lufs']:.2f}", target=f"{result['target_lufs']:.2f}")
        )


    def reset_ui(self):
        self.progress.hide()
        self.label_status.setText("")
        self.label_preview.hide()
        self.preview_section.hide()
        self.button_save.hide()
        self.hint_label.hide()

    def set_inputs_enabled(self, enabled):
        for widget in [self.button_browse, self.entry_gain, self.cb_eq, self.cb_width, self.cb_sat,
                       self.entry_file, self.button_process, self.platform_selector]:
            widget.setEnabled(enabled)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("select_file"), os.getcwd(), "WAV Files (*.wav)")
        if file_path:
            self.entry_file.setText(file_path)

    def process_audio(self):
        file_path = self.entry_file.text()
        if not os.path.isfile(file_path):
            self.label_status.setText("Invalid file.")
            return

        try:
            gain = float(self.entry_gain.text())
        except ValueError:
            self.label_status.setText(self.tr("gain_error"))
            return

        use_eq = self.cb_eq.isChecked()
        use_width = self.cb_width.isChecked()
        use_sat = self.cb_sat.isChecked()
        platform = self.current_platform

        print("🔄 Starting mastering thread...")
        self.set_inputs_enabled(False)
        self.label_status.setText(self.tr("processing"))
        self.progress.setValue(0)
        self.progress.show()
        self.label_preview.hide()
        self.preview_section.hide()
        self.button_save.hide()
        self.hint_label.hide()

        def run_mastering():
            try:
                def callback(val):
                    print(f"📶 Progress: {val}%")
                    self.progress.setValue(val)

                self.original_audio, self.mastered_audio, self.last_preset = master_audio(
                    file_path, gain, use_eq, use_width, use_sat, platform, callback
                )
                print("✅ Mastering finished. Calling show_preview...")
                QMetaObject.invokeMethod(self, self.show_preview.__name__, Qt.QueuedConnection)

            except Exception as e:
                print(f"❌ Error during mastering: {e}")
                QTimer.singleShot(0, lambda: self.label_status.setText(f"Error: {str(e)}"))
                self.set_inputs_enabled(True)

        threading.Thread(target=run_mastering).start()

    @Slot()
    def show_preview(self):
        print("📺 Running show_preview...")
        self.label_status.setText(self.tr("mastering_complete"))

        for preview_widget in [self.original_preview, self.mastered_preview]:
            layout = preview_widget.layout()
            while layout.count():
                layout.itemAt(0).widget().deleteLater()

        self.original_preview.layout().addWidget(AudioPlayerWidget(self.original_audio))
        self.mastered_preview.layout().addWidget(AudioPlayerWidget(self.mastered_audio))

        self.progress.hide()
        self.label_preview.show()
        self.preview_section.show()
        self.button_save.show()

        data = np.array(self.mastered_audio.get_array_of_samples()).astype(np.float32)
        if data.ndim == 1:
            data = np.stack([data, data], axis=1)
        loudness = analyze_loudness(data)
        target = self.last_preset["target_lufs"]
        hint = get_loudness_hint_for_lang(loudness, target, self.current_lang)
        print(f"💡 Hint: {hint}")
        self.hint_label.setText(f"💡 {hint}")
        self.hint_label.show()

        self.set_inputs_enabled(True)

    def save_output(self):
        if not self.mastered_audio:
            self.label_status.setText(self.tr("no_audio"))
            return

        output_path, _ = QFileDialog.getSaveFileName(self, self.tr("save"), os.getcwd(), "WAV Files (*.wav)")
        if output_path:
            print(f"💾 Saving mastered audio to: {output_path}")
            self.mastered_audio.export(output_path, format="wav")

            original_data = np.array(self.original_audio.get_array_of_samples()).astype(np.float32)
            processed_data, _ = sf.read(output_path)
            before = analyze_loudness(original_data)
            after = analyze_loudness(processed_data)

            print(f"📈 Loudness Before: {before:.2f} dB | After: {after:.2f} dB")
            self.label_status.setText(
                self.tr("saved_loudness", before=f"{before:.2f}", after=f"{after:.2f}")
            )

    def change_language(self):
        selected = self.combo_lang.currentText()
        self.current_lang = "id" if selected == "Bahasa Indonesia" else "en"
        self.settings["lang"] = self.current_lang
        self.save_settings()
        self.update_ui_texts()

    def update_ui_texts(self):
        self.label_select.setText(self.tr("select_file"))
        self.button_browse.setText(self.tr("browse"))
        self.label_gain.setText(self.tr("gain_label"))
        self.cb_eq.setText(self.tr("eq"))
        self.cb_width.setText(self.tr("width"))
        self.cb_sat.setText(self.tr("saturation"))
        self.platform_label.setText(self.tr("platform"))
        self.button_process.setText(self.tr("start"))
        self.button_save.setText(self.tr("save"))
        self.label_preview.setText(self.tr("preview"))
        self.combo_lang.setCurrentIndex(1 if self.current_lang == "id" else 0)
        self.label_status.setText("")