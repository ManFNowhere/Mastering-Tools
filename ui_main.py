from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout,
    QCheckBox, QProgressBar, QFileDialog, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, QMetaObject, Slot
import os
import threading
import json
import soundfile as sf
import numpy as np
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
from scripts.mastering import master_audio
from scripts.utils import analyze_loudness, get_loudness_hint_for_lang
from scripts.presets import platform_presets
from scripts.audio_player_widget import AudioPlayerWidget
from scripts.recommender import recommend_gain
from scripts.custom_processing_dialog import CustomSettingsPopup
from scripts.utils import analyze_loudness, analyze_peak_rms, get_loudness_hint_for_lang

class MasteringApp(QWidget):
    def __init__(self):
        super().__init__()
        print("\U0001f527 Initializing MasteringApp GUI...")
        self.setWindowTitle("Mastering Tool - Secret Silence")
        self.setMinimumWidth(700)
        self.load_settings()
        self.load_language()
        self._player_widgets = []
        self._mastering_thread = None
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
        print("\U0001f310 Loading language JSON...")
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
        self.button_browse = QPushButton(self.tr("browse"))
        self.button_browse.clicked.connect(self.browse_file)

        file_layout = QHBoxLayout()
        file_layout.addWidget(self.label_select)
        file_layout.addWidget(self.entry_file)
        file_layout.addWidget(self.button_browse)

        self.label_gain = QLabel(self.tr("gain_label"))
        self.entry_gain = QLineEdit("0.0")
        self.button_recommend_gain = QPushButton(self.tr("recommend_gain"))
        self.button_recommend_gain.clicked.connect(self.apply_recommended_gain)

        self.cb_eq = QCheckBox(self.tr("eq"))
        self.cb_width = QCheckBox(self.tr("width"))
        self.cb_sat = QCheckBox(self.tr("saturation"))

        self.platform_label = QLabel(self.tr("platform"))
        self.platform_selector = QComboBox()
        self.platform_selector.addItems(platform_presets.keys())
        self.platform_selector.setCurrentText("Spotify")
        self.platform_selector.currentTextChanged.connect(lambda p: setattr(self, "current_platform", p))

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

        self.button_customize = QPushButton("⚙ Customize")
        self.button_customize.clicked.connect(self.open_custom_popup)
        lang_layout.addWidget(self.button_customize)

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

    def open_custom_popup(self):
        popup = CustomSettingsPopup(lang=self.current_lang)
        popup.exec()

    def reset_preview_and_threads(self):
        print("🔁 Resetting previous preview and threads...")

        for preview_widget in [self.original_preview, self.mastered_preview]:
            layout = preview_widget.layout()
            for i in reversed(range(layout.count())):
                widget = layout.itemAt(i).widget()
                if hasattr(widget, "stop"):
                    widget.stop()
                widget.deleteLater()

        self._player_widgets.clear()
        self.preview_section.hide()
        self.progress.setValue(0)

        if self._mastering_thread and self._mastering_thread.is_alive():
            print("⏳ Waiting for previous mastering thread to end...")
            self._mastering_thread.join(timeout=1.0)

    def set_inputs_enabled(self, enabled):
        for widget in [self.button_browse, self.entry_gain, self.cb_eq, self.cb_width, self.cb_sat,
                       self.entry_file, self.button_process, self.platform_selector]:
            widget.setEnabled(enabled)

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, self.tr("select_file"), os.getcwd(), "WAV Files (*.wav)")
        if file_path:
            print(f"📁 New file selected: {file_path}")
            self.entry_file.setText(file_path)

    
    def process_audio(self):
        file_path = self.entry_file.text()
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "File Error", "The selected file does not exist.")
            return

        if not file_path.lower().endswith(".wav"):
            QMessageBox.warning(self, "Unsupported Format", "Only WAV files are supported.")
            return

        try:
            gain = float(self.entry_gain.text())
        except ValueError:
            QMessageBox.warning(self, "Invalid Gain", "Please enter a valid number for gain.")
            return

        use_eq = self.cb_eq.isChecked()
        use_width = self.cb_width.isChecked()
        use_sat = self.cb_sat.isChecked()
        platform = self.current_platform

        print("🟡 Requested to master:", file_path)
        self.reset_preview_and_threads()

        self.label_status.hide()
        self.hint_label.hide()
        self.label_preview.hide()
        self.preview_section.hide()
        self.button_save.hide()

        self.progress.setValue(0)
        self.progress.show()
        self.label_status.setText(self.tr("processing"))
        self.label_status.show()
        self.set_inputs_enabled(False)

        def run_mastering():
            try:
                def callback(val):
                    print(f"📶 Progress: {val}%")
                    self.progress.setValue(val)

                self.original_audio, self.mastered_audio, self.last_preset = master_audio(
                    file_path, gain, use_eq, use_width, use_sat, platform, callback
                )
                QMetaObject.invokeMethod(self, self.show_preview.__name__, Qt.QueuedConnection)

            except ValueError as ve:
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", str(ve)))
            except CouldntDecodeError:
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", "Unable to decode the audio file."))
            except Exception as e:
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", f"An error occurred: {e}"))
            finally:
                self.set_inputs_enabled(True)

        self._mastering_thread = threading.Thread(target=run_mastering, daemon=True)
        self._mastering_thread.start()

    @Slot()
    def show_preview(self):
        print("📺 Running show_preview...")
        self.label_status.setText(self.tr("mastering_complete"))

        # 🔊 Original Audio
        player1 = AudioPlayerWidget(self.original_audio)
        original_data = np.array(self.original_audio.get_array_of_samples()).astype(np.float32)
        if original_data.ndim == 1:
            original_data = np.stack([original_data, original_data], axis=1)
        original_peak, original_rms = analyze_peak_rms(original_data)
        # label_orig_stats = QLabel(f"🔊 Peak: {original_peak:.2f} dB | RMS: {original_rms:.2f} dB")

        # 🔊 Mastered Audio
        player2 = AudioPlayerWidget(self.mastered_audio)
        mastered_data = np.array(self.mastered_audio.get_array_of_samples()).astype(np.float32)
        if mastered_data.ndim == 1:
            mastered_data = np.stack([mastered_data, mastered_data], axis=1)
        mastered_peak, mastered_rms = analyze_peak_rms(mastered_data)
        # label_mast_stats = QLabel(f"🎧 Peak: {mastered_peak:.2f} dB | RMS: {mastered_rms:.2f} dB")

        # 🧠 Loudness Hint
        loudness = analyze_loudness(mastered_data)
        target = self.last_preset["target_lufs"]
        hint = get_loudness_hint_for_lang(loudness, target, self.current_lang)
        print(f"💡 Hint: {hint}")
        self.hint_label.setText(f"💡 {hint}")
        self.hint_label.show()

        # 🧱 Add to Layouts
        self.original_preview.layout().addWidget(player1)
        # self.original_preview.layout().addWidget(label_orig_stats)

        self.mastered_preview.layout().addWidget(player2)
        # self.mastered_preview.layout().addWidget(label_mast_stats)

        self._player_widgets = [player1, player2]
        self.progress.hide()
        self.label_preview.show()
        self.preview_section.show()
        self.button_save.show()
        self.set_inputs_enabled(True)



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
    
    def save_output(self):
        if not self.mastered_audio:
            self.label_status.setText(self.tr("no_audio"))
            return

        output_path, _ = QFileDialog.getSaveFileName(self, self.tr("save"), os.getcwd(), "WAV Files (*.wav)")
        if output_path:
            print(f"💾 Saving mastered audio to: {output_path}")
            self.mastered_audio.export(output_path, format="wav")

            # --- ANALISIS BEFORE/AFTER DENGAN SKALA YANG BENAR ---
            original_data = np.array(self.original_audio.get_array_of_samples()).astype(np.float32)
            if np.max(np.abs(original_data)) > 1.5:
                original_data /= 32768.0
            if original_data.ndim == 1:
                original_data = np.stack([original_data, original_data], axis=1)

            processed_data, _ = sf.read(output_path)
            if processed_data.ndim == 1:
                processed_data = np.stack([processed_data, processed_data], axis=1)

            # --- Loudness / Peak / RMS ---
            before_loud = analyze_loudness(original_data)
            after_loud = analyze_loudness(processed_data)
            before_peak, before_rms = analyze_peak_rms(original_data)
            after_peak, after_rms = analyze_peak_rms(processed_data)

            print(f"📈 Loudness Before: {before_loud:.2f} dB | After: {after_loud:.2f} dB")

            # --- Simpan metadata .json ---
            metadata = {
                "platform": self.current_platform,
                "target_lufs": float(self.last_preset["target_lufs"]),
                "gain_applied": float(self.entry_gain.text()),
                "loudness_before": float(before_loud),
                "loudness_after": float(after_loud),
                "peak_before": float(before_peak),
                "peak_after": float(after_peak),
                "rms_before": float(before_rms),
                "rms_after": float(after_rms)
            }
            json_path = output_path.replace(".wav", ".json")
            with open(json_path, "w") as f:
                json.dump(metadata, f, indent=4)

            self.label_status.setText(
                self.tr("saved_loudness", before=f"{before_loud:.2f}", after=f"{after_loud:.2f}")
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