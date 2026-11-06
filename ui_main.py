import os, threading, json
import numpy as np
import soundfile as sf

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout,
    QCheckBox, QProgressBar, QFileDialog, QComboBox, QMessageBox, QFrame,
)
from PySide6.QtCore import Qt, QTimer, QMetaObject, Slot, Signal
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor, QPen, QFont

from scripts.mastering import master_audio
from scripts.utils import analyze_loudness, analyze_peak_rms, get_loudness_hint_for_lang
from scripts.presets import platform_presets
from scripts.recommender import recommend_gain
from scripts.custom_processing_dialog import CustomSettingsPopup
from scripts.comparison_player import ComparisonPlayerWidget

# ─────────────────────────────────────────────────────────────
#  Colour tokens
# ─────────────────────────────────────────────────────────────
C_BG       = "#0A0A0A"
C_SURFACE  = "#141414"
C_BORDER   = "#2A2A2A"
C_ACCENT   = "#F5C518"   # yellow
C_ACCENT_H = "#FFD740"   # hover yellow
C_ACCENT_P = "#C49B00"   # pressed yellow
C_TEXT     = "#EEEEEE"
C_MUTED    = "#666666"

# ─────────────────────────────────────────────────────────────
#  Global stylesheet
# ─────────────────────────────────────────────────────────────
GLOBAL_STYLE = f"""
QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-size: 13px;
}}

/* ── inputs ── */
QLineEdit {{
    background-color: {C_SURFACE};
    border: 1.5px solid {C_BORDER};
    border-radius: 6px;
    padding: 8px 12px;
    color: {C_TEXT};
}}
QLineEdit:focus  {{ border-color: {C_ACCENT}; }}
QLineEdit:read-only {{ color: #888888; }}
QLineEdit:disabled {{ background: #0D0D0D; color: #333333; border-color: #1A1A1A; }}

/* ── combobox ── */
QComboBox {{
    background-color: {C_SURFACE};
    border: 1.5px solid {C_BORDER};
    border-radius: 6px;
    padding: 8px 36px 8px 12px;
    color: {C_TEXT};
    min-width: 90px;
}}
QComboBox:hover {{ border-color: {C_ACCENT}; }}
QComboBox:disabled {{ background: #0D0D0D; color: #333333; border-color: #1A1A1A; }}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 28px;
    border: none;
}}
QComboBox::down-arrow {{
    image: url(assets/arrow-down.svg);
    width: 12px;
    height: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: #1A1A1A;
    border: 1px solid {C_BORDER};
    color: {C_TEXT};
    selection-background-color: #252500;
    selection-color: {C_ACCENT};
    outline: none;
    padding: 4px;
}}

/* ── checkbox ── */
QCheckBox {{ spacing: 14px; color: #AAAAAA; }}
QCheckBox:hover {{ color: {C_TEXT}; }}
QCheckBox:disabled {{ color: #333333; }}
QCheckBox::indicator {{
    width: 18px; height: 18px;
    border: 1.5px solid #3A3A3A;
    border-radius: 4px;
    background: {C_SURFACE};
}}
QCheckBox::indicator:hover   {{ border-color: {C_ACCENT}; }}
QCheckBox::indicator:checked {{
    background-color: {C_ACCENT};
    border-color: {C_ACCENT};
    image: url(assets/check.svg);
}}
QCheckBox::indicator:disabled {{ border-color: #222222; background: #0D0D0D; }}

/* ── progress ── */
QProgressBar {{
    background-color: #1A1A1A;
    border: none;
    border-radius: 4px;
    max-height: 8px;
    color: transparent;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {C_ACCENT};
    border-radius: 4px;
}}

/* ── slider ── */
QSlider::groove:horizontal {{
    background: #1E1E1E; height: 4px; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {C_ACCENT}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {C_ACCENT};
    width: 14px; height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}}
QSlider::handle:horizontal:hover {{ background: {C_ACCENT_H}; }}
QSlider:disabled::groove:horizontal  {{ background: #111111; }}
QSlider:disabled::handle:horizontal  {{ background: #333333; }}

/* ── scrollbar ── */
QScrollBar:vertical {{ background: {C_BG}; width: 6px; border-radius: 3px; }}
QScrollBar::handle:vertical {{ background: #2A2A2A; border-radius: 3px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
"""

# ─────────────────────────────────────────────────────────────
#  Button styles
# ─────────────────────────────────────────────────────────────
BTN_PRIMARY = f"""
QPushButton {{
    background-color: {C_ACCENT};
    color: #000000;
    font-size: 14px; font-weight: 700;
    border: none; border-radius: 8px;
    letter-spacing: 0.5px;
}}
QPushButton:hover   {{ background-color: {C_ACCENT_H}; }}
QPushButton:pressed {{ background-color: {C_ACCENT_P}; }}
QPushButton:disabled {{ background-color: #2A2500; color: #555500; }}
"""

BTN_SECONDARY = f"""
QPushButton {{
    background-color: {C_SURFACE};
    color: {C_ACCENT};
    border: 1.5px solid {C_ACCENT};
    border-radius: 8px;
    font-size: 13px; font-weight: 600;
}}
QPushButton:hover   {{ background-color: #1E1900; color: {C_ACCENT_H}; }}
QPushButton:pressed {{ background-color: #141000; }}
QPushButton:disabled {{ background-color: #0D0D0D; color: #3A3000; border-color: #2A2000; }}
"""

BTN_GHOST = f"""
QPushButton {{
    background-color: {C_SURFACE};
    color: {C_MUTED};
    border: 1px solid {C_BORDER};
    border-radius: 7px;
    font-size: 12px;
    padding: 7px 14px;
}}
QPushButton:hover {{ background-color: #1E1E1E; color: #CCCCCC; border-color: #3A3A3A; }}
"""

BTN_SAVING = f"""
QPushButton {{
    background-color: #1E1A00;
    color: #888800;
    font-size: 14px; font-weight: 700;
    border: none; border-radius: 8px;
}}
"""

BTN_SUCCESS = """
QPushButton {
    background-color: #0E3B1A;
    color: #22C55E;
    font-size: 14px; font-weight: 700;
    border: none; border-radius: 8px;
}
"""

SEP_STYLE   = f"QFrame {{ background: {C_BORDER}; max-height: 1px; border: none; }}"
LABEL_SECTION = f"color: {C_ACCENT}; font-size: 10px; font-weight: 700; letter-spacing: 2px;"
LABEL_FIELD   = f"color: {C_MUTED}; font-size: 12px;"
HINT_STYLE    = (
    f"background: #111100; border-left: 3px solid {C_ACCENT}; border-radius: 4px;"
    f" padding: 8px 14px; color: #CCAA00; font-size: 12px;"
)
STATUS_STYLE  = f"color: {C_MUTED}; font-size: 12px;"


def _sep():
    f = QFrame()
    f.setFrameShape(QFrame.HLine)
    f.setStyleSheet(SEP_STYLE)
    return f


def _sec(text: str) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(LABEL_SECTION)
    return l


# ─────────────────────────────────────────────────────────────
#  Waveform placeholder (shown before first mastering)
# ─────────────────────────────────────────────────────────────
class _WaveformPlaceholder(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(160)

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        p = QPainter(self)
        p.fillRect(0, 0, w, h, QColor(14, 14, 14))

        # decorative silent waveform
        p.setPen(QPen(QColor(35, 35, 35), 1))
        mid = h // 2
        import math
        for x in range(0, w, 2):
            amp = math.sin(x * 0.05) * 8 + math.sin(x * 0.017) * 14
            p.drawLine(x, int(mid - amp), x, int(mid + amp))

        p.setPen(QColor(55, 55, 55))
        font = QFont()
        font.setPointSize(10)
        p.setFont(font)
        p.drawText(0, 0, w, h, Qt.AlignCenter,
                   "Load a file and run mastering\nto see the comparison preview")
        p.end()


# ─────────────────────────────────────────────────────────────
#  Main window
# ─────────────────────────────────────────────────────────────
class MasteringApp(QWidget):
    _sig_save_progress = Signal(int, str)      # pct, message
    _sig_save_complete = Signal(float, float)  # loudness before, after
    _sig_save_error    = Signal(str)           # error message

    def __init__(self):
        super().__init__()
        self.setWindowTitle("SS-Mastering")
        if os.path.exists("mastering_tool_icon.ico"):
            self.setWindowIcon(QIcon("mastering_tool_icon.ico"))

        self.setMinimumSize(900, 700)
        self.resize(960, 760)

        self.load_settings()
        self.load_language()

        self._sig_save_progress.connect(self._on_save_progress)
        self._sig_save_complete.connect(self._on_save_complete)
        self._sig_save_error.connect(self._on_save_error)

        self._mastering_thread  = None
        self._comparison_player = None
        self.original_audio = None
        self.mastered_audio = None
        self.current_platform = "Spotify"
        self.last_preset = None

        self.setup_ui()
        self.setStyleSheet(GLOBAL_STYLE)

    # ── settings / i18n ──────────────────────────────────────

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
        with open("lang.json", "r", encoding="utf-8") as f:
            self.lang_data = json.load(f)
        self.current_lang = self.settings.get("lang", "en")

    def tr(self, key, **kwargs):
        text = self.lang_data.get(self.current_lang, {}).get(key, key)
        return text.format(**kwargs) if kwargs else text

    # ── UI construction ──────────────────────────────────────

    def setup_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(28, 22, 28, 22)
        root.setSpacing(14)
        self.setLayout(root)

        # ── HEADER ───────────────────────────────────────────
        logo_lbl = QLabel()
        if os.path.exists("logo.png"):
            px = QPixmap("logo.png").scaled(
                56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            logo_lbl.setPixmap(px)

        title_lbl = QLabel("SS-Mastering")
        title_lbl.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #FFFFFF; letter-spacing: 1px;"
        )
        sub_lbl = QLabel("Audio Mastering Tool")
        sub_lbl.setStyleSheet("font-size: 11px; color: #444444; margin-top: -4px;")

        title_col = QVBoxLayout()
        title_col.setSpacing(1)
        title_col.addWidget(title_lbl)
        title_col.addWidget(sub_lbl)

        self.label_language = QLabel(self.tr("language"))
        self.label_language.setStyleSheet(LABEL_FIELD)

        self.combo_lang = QComboBox()
        self.combo_lang.addItems(["English", "Bahasa Indonesia"])
        self.combo_lang.setCurrentIndex(1 if self.current_lang == "id" else 0)
        self.combo_lang.setFixedWidth(150)
        self.combo_lang.setFixedHeight(36)
        self.combo_lang.currentIndexChanged.connect(self.change_language)

        self.button_customize = QPushButton("Customize")
        self.button_customize.setStyleSheet(BTN_GHOST)
        self.button_customize.setFixedHeight(36)
        self.button_customize.clicked.connect(self.open_custom_popup)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        header_row.addWidget(logo_lbl)
        header_row.addSpacing(8)
        header_row.addLayout(title_col)
        header_row.addStretch()
        header_row.addWidget(self.label_language)
        header_row.addWidget(self.combo_lang)
        header_row.addSpacing(6)
        header_row.addWidget(self.button_customize)

        root.addLayout(header_row)
        root.addWidget(_sep())

        # ── FILE ─────────────────────────────────────────────
        root.addWidget(_sec("AUDIO FILE"))

        self.entry_file = QLineEdit()
        self.entry_file.setReadOnly(True)
        self.entry_file.setFixedHeight(40)
        self.entry_file.setPlaceholderText("No file selected — choose a stereo WAV file…")

        self.button_browse = QPushButton(self.tr("browse"))
        self.button_browse.setStyleSheet(BTN_SECONDARY)
        self.button_browse.setFixedHeight(40)
        self.button_browse.setFixedWidth(100)
        self.button_browse.clicked.connect(self.browse_file)

        file_row = QHBoxLayout()
        file_row.setSpacing(8)
        file_row.addWidget(self.entry_file)
        file_row.addWidget(self.button_browse)
        root.addLayout(file_row)
        root.addWidget(_sep())

        # ── SETTINGS ─────────────────────────────────────────
        root.addWidget(_sec("SETTINGS"))

        self.lbl_gain = QLabel(self.tr("gain_label"))
        self.lbl_gain.setStyleSheet(LABEL_FIELD)
        self.entry_gain = QLineEdit("0.0")
        self.entry_gain.setFixedWidth(72)
        self.entry_gain.setFixedHeight(38)
        self.entry_gain.setAlignment(Qt.AlignCenter)

        self.button_auto = QPushButton(self.tr("auto_gain"))
        self.button_auto.setStyleSheet(BTN_SECONDARY)
        self.button_auto.setFixedHeight(38)
        self.button_auto.clicked.connect(self.apply_recommended_gain)

        vd = QFrame()
        vd.setFrameShape(QFrame.VLine)
        vd.setStyleSheet(f"QFrame {{ background: {C_BORDER}; max-width: 1px; }}")

        self.lbl_platform = QLabel(self.tr("platform"))
        self.lbl_platform.setStyleSheet(LABEL_FIELD)
        self.platform_selector = QComboBox()
        self.platform_selector.addItems(platform_presets.keys())
        self.platform_selector.setCurrentText("Spotify")
        self.platform_selector.setFixedHeight(38)
        self.platform_selector.currentTextChanged.connect(
            lambda p: setattr(self, "current_platform", p)
        )

        vd2 = QFrame()
        vd2.setFrameShape(QFrame.VLine)
        vd2.setStyleSheet(f"QFrame {{ background: {C_BORDER}; max-width: 1px; }}")

        self.cb_eq    = QCheckBox(self.tr("eq"))
        self.cb_width = QCheckBox(self.tr("width"))
        self.cb_sat   = QCheckBox(self.tr("saturation"))

        settings_row = QHBoxLayout()
        settings_row.setSpacing(10)
        settings_row.addWidget(self.lbl_gain)
        settings_row.addWidget(self.entry_gain)
        settings_row.addWidget(self.button_auto)
        settings_row.addSpacing(8)
        settings_row.addWidget(vd)
        settings_row.addSpacing(8)
        settings_row.addWidget(self.lbl_platform)
        settings_row.addWidget(self.platform_selector)
        settings_row.addSpacing(8)
        settings_row.addWidget(vd2)
        settings_row.addSpacing(8)
        settings_row.addWidget(self.cb_eq)
        settings_row.addSpacing(14)
        settings_row.addWidget(self.cb_width)
        settings_row.addSpacing(14)
        settings_row.addWidget(self.cb_sat)
        settings_row.addStretch()
        root.addLayout(settings_row)

        root.addWidget(_sep())

        # ── START MASTERING ───────────────────────────────────
        self.button_process = QPushButton(self.tr("start").upper())
        self.button_process.setStyleSheet(BTN_PRIMARY)
        self.button_process.setFixedHeight(52)
        self.button_process.clicked.connect(self.process_audio)
        root.addWidget(self.button_process)

        self.progress = QProgressBar()
        self.progress.hide()
        root.addWidget(self.progress)

        self.label_status = QLabel("")
        self.label_status.setStyleSheet(STATUS_STYLE)
        self.label_status.setAlignment(Qt.AlignCenter)
        self.label_status.hide()
        root.addWidget(self.label_status)

        root.addWidget(_sep())

        # ── PREVIEW (always visible) ──────────────────────────
        root.addWidget(_sec("PREVIEW — COMPARE"))

        # container: starts with placeholder, swapped after mastering
        self._preview_container = QWidget()
        self._preview_container.setLayout(QVBoxLayout())
        self._preview_container.layout().setContentsMargins(0, 0, 0, 0)
        self._preview_container.layout().addWidget(_WaveformPlaceholder())
        root.addWidget(self._preview_container)

        self.hint_label = QLabel("")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(HINT_STYLE)
        self.hint_label.hide()
        root.addWidget(self.hint_label)

        root.addWidget(_sep())

        # ── EXPORT (always visible) ───────────────────────────
        root.addWidget(_sec("EXPORT"))

        self.lbl_format = QLabel("Format:")
        self.lbl_format.setStyleSheet(LABEL_FIELD)

        self.export_format = QComboBox()
        self.export_format.addItems(["WAV  (.wav)", "FLAC  (.flac)", "MP3  (.mp3)"])
        self.export_format.setFixedHeight(40)
        self.export_format.setFixedWidth(150)

        self.button_save = QPushButton(self.tr("save"))
        self.button_save.setStyleSheet(BTN_PRIMARY)
        self.button_save.setFixedHeight(40)
        self.button_save.setEnabled(False)
        self.button_save.clicked.connect(self.save_output)

        export_row = QHBoxLayout()
        export_row.setSpacing(10)
        export_row.addWidget(self.lbl_format)
        export_row.addWidget(self.export_format)
        export_row.addSpacing(8)
        export_row.addWidget(self.button_save)
        root.addLayout(export_row)

        root.addStretch()

    # ── helpers ───────────────────────────────────────────────

    def open_custom_popup(self):
        CustomSettingsPopup(lang=self.current_lang).exec()

    def set_inputs_enabled(self, enabled: bool):
        for w in (
            self.button_browse, self.entry_file, self.entry_gain,
            self.cb_eq, self.cb_width, self.cb_sat,
            self.button_process, self.platform_selector, self.button_auto,
        ):
            w.setEnabled(enabled)

    def _clear_preview(self):
        if self._comparison_player is not None:
            self._comparison_player.cleanup()
            self._comparison_player = None
        lay = self._preview_container.layout()
        while lay.count():
            item = lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _reset_for_processing(self):
        self._clear_preview()
        self._preview_container.layout().addWidget(_WaveformPlaceholder())
        self.hint_label.hide()
        self.button_save.setEnabled(False)
        self.label_status.hide()
        self.progress.setValue(0)
        if self._mastering_thread and self._mastering_thread.is_alive():
            self._mastering_thread.join(timeout=1.0)

    # ── file / gain ───────────────────────────────────────────

    def browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr("select_file"), os.getcwd(), "WAV Files (*.wav)"
        )
        if path:
            self.entry_file.setText(path)

    def apply_recommended_gain(self):
        path = self.entry_file.text()
        if not os.path.isfile(path):
            self.label_status.setText(self.tr("file_error"))
            self.label_status.show()
            return
        result = recommend_gain(path, self.current_platform)
        self.entry_gain.setText(f"{result['recommended_gain']:.2f}")
        self.label_status.setText(
            self.tr("gain_recommended",
                    current=f"{result['current_lufs']:.2f}",
                    target=f"{result['target_lufs']:.2f}")
        )
        self.label_status.show()

    # ── mastering ─────────────────────────────────────────────

    def process_audio(self):
        path = self.entry_file.text()
        if not os.path.isfile(path):
            QMessageBox.warning(self, "Error", self.tr("file_error"))
            return
        if not path.lower().endswith(".wav"):
            QMessageBox.warning(self, "Error", self.tr("format_error"))
            return
        try:
            gain = float(self.entry_gain.text())
        except ValueError:
            QMessageBox.warning(self, "Error", self.tr("invalid_gain"))
            return

        self._reset_for_processing()
        self.progress.setValue(0)
        self.progress.show()
        self.label_status.setText(self.tr("processing"))
        self.label_status.show()
        self.set_inputs_enabled(False)

        use_eq    = self.cb_eq.isChecked()
        use_width = self.cb_width.isChecked()
        use_sat   = self.cb_sat.isChecked()
        platform  = self.current_platform

        def run():
            try:
                self.original_audio, self.mastered_audio, self.last_preset = master_audio(
                    path, gain, use_eq, use_width, use_sat, platform,
                    lambda v: self.progress.setValue(v),
                )
                QMetaObject.invokeMethod(self, self._show_preview.__name__, Qt.QueuedConnection)
            except ValueError as e:
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "Error", str(e)))
            except CouldntDecodeError:
                QTimer.singleShot(0, lambda: QMessageBox.critical(
                    self, "Error", "Cannot decode audio file."))
            except Exception as e:
                QTimer.singleShot(0, lambda: QMessageBox.critical(
                    self, "Error", f"Unexpected error: {e}"))
            finally:
                self.set_inputs_enabled(True)

        self._mastering_thread = threading.Thread(target=run, daemon=True)
        self._mastering_thread.start()

    @Slot()
    def _show_preview(self):
        self._clear_preview()

        player = ComparisonPlayerWidget(self.original_audio, self.mastered_audio)
        self._comparison_player = player
        self._preview_container.layout().addWidget(player)

        mdata = np.array(self.mastered_audio.get_array_of_samples()).astype(np.float32)
        if mdata.ndim == 1:
            mdata = np.stack([mdata, mdata], axis=1)
        if np.max(np.abs(mdata)) > 1.5:
            mdata /= 32768.0
        loudness = analyze_loudness(mdata)
        hint = get_loudness_hint_for_lang(loudness, self.last_preset["target_lufs"], self.current_lang)
        self.hint_label.setText(f"  {hint}")
        self.hint_label.show()

        self.progress.hide()
        self.label_status.setText(self.tr("mastering_complete"))
        self.label_status.show()
        self.button_save.setEnabled(True)

    # ── save ──────────────────────────────────────────────────

    def save_output(self):
        if not self.mastered_audio:
            return

        fmt_text = self.export_format.currentText()
        ext = "." + fmt_text.split("(.")[-1].rstrip(")")
        fmt = ext.lstrip(".")

        filter_map = {
            ".wav":  "WAV Files (*.wav)",
            ".flac": "FLAC Files (*.flac)",
            ".mp3":  "MP3 Files (*.mp3)",
        }
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("save"), os.getcwd(), filter_map.get(ext, "WAV Files (*.wav)")
        )
        if not path:
            return
        if not path.lower().endswith(ext):
            path += ext

        self.button_save.setEnabled(False)
        self.button_save.setStyleSheet(BTN_SAVING)
        self.button_save.setText("Saving... 0%")
        self.progress.setValue(0)
        self.progress.show()
        self.label_status.setText("Starting save…")
        self.label_status.show()

        def prog(pct: int, msg: str):
            print(f"[Save] {pct:3d}% — {msg}")
            self._sig_save_progress.emit(pct, msg)  # thread-safe signal

        def do_save():
            try:
                prog(5, f"Exporting audio to {fmt.upper()}…")
                self.mastered_audio.export(path, format=fmt)
                print(f"[Save]  export done → {path}")

                prog(55, "Analyzing original audio…")
                odata = np.array(self.original_audio.get_array_of_samples()).astype(np.float32)
                if np.max(np.abs(odata)) > 1.5:
                    odata /= 32768.0
                if odata.ndim == 1:
                    odata = np.stack([odata, odata], axis=1)

                prog(70, "Reading exported file…")
                pdata, _ = sf.read(path)
                if pdata.ndim == 1:
                    pdata = np.stack([pdata, pdata], axis=1)

                prog(80, "Measuring loudness (LUFS)…")
                bl = analyze_loudness(odata)
                al = analyze_loudness(pdata)
                print(f"[Save]  loudness — before: {bl:.2f} LUFS  after: {al:.2f} LUFS")

                prog(90, "Measuring peak / RMS…")
                bp, br = analyze_peak_rms(odata)
                ap, ar = analyze_peak_rms(pdata)
                print(f"[Save]  peak — before: {bp:.2f} dB  after: {ap:.2f} dB")

                prog(97, "Writing metadata…")
                metadata = {
                    "platform":        self.current_platform,
                    "target_lufs":     float(self.last_preset["target_lufs"]),
                    "gain_applied":    float(self.entry_gain.text()),
                    "loudness_before": float(bl),
                    "loudness_after":  float(al),
                    "peak_before":     float(bp),
                    "peak_after":      float(ap),
                    "rms_before":      float(br),
                    "rms_after":       float(ar),
                }
                meta_path = os.path.splitext(path)[0] + "_metadata.json"
                with open(meta_path, "w") as f:
                    json.dump(metadata, f, indent=4)
                print(f"[Save]  metadata → {meta_path}")
                print(f"[Save] Complete.")

                self._sig_save_complete.emit(bl, al)
            except Exception as e:
                err = str(e)
                print(f"[Save] ERROR — {err}")
                self._sig_save_error.emit(err)

        threading.Thread(target=do_save, daemon=True).start()

    @Slot(int, str)
    def _on_save_progress(self, pct: int, msg: str):
        self.button_save.setText(f"Saving... {pct}%")
        self.progress.setValue(pct)
        self.label_status.setText(msg)

    @Slot(float, float)
    def _on_save_complete(self, bl: float, al: float):
        self.progress.setValue(100)
        QTimer.singleShot(800, self.progress.hide)
        self.button_save.setStyleSheet(BTN_SUCCESS)
        self.button_save.setText("Saved! 100%")
        self.label_status.setText(
            self.tr("saved_loudness", before=f"{bl:.2f}", after=f"{al:.2f}")
        )
        self.label_status.show()
        QTimer.singleShot(2500, self._reset_save_button)

    @Slot(str)
    def _on_save_error(self, msg: str):
        self.progress.hide()
        self._reset_save_button()
        QMessageBox.critical(self, "Save Failed", msg)

    def _reset_save_button(self):
        self.button_save.setText(self.tr("save"))
        self.button_save.setStyleSheet(BTN_PRIMARY)
        self.button_save.setEnabled(True)

    # ── language ──────────────────────────────────────────────

    def change_language(self):
        self.current_lang = "id" if self.combo_lang.currentIndex() == 1 else "en"
        self.settings["lang"] = self.current_lang
        self.save_settings()
        self.update_ui_texts()

    def update_ui_texts(self):
        self.button_browse.setText(self.tr("browse"))
        self.lbl_gain.setText(self.tr("gain_label"))
        self.button_auto.setText(self.tr("auto_gain"))
        self.lbl_platform.setText(self.tr("platform"))
        self.cb_eq.setText(self.tr("eq"))
        self.cb_width.setText(self.tr("width"))
        self.cb_sat.setText(self.tr("saturation"))
        self.button_process.setText(self.tr("start").upper())
        self.button_save.setText(self.tr("save"))
        self.label_language.setText(self.tr("language"))
