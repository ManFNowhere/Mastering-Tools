from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import Qt, QTimer
import numpy as np
from scripts.utils import analyze_loudness, analyze_peak_rms, get_loudness_hint_for_lang

class StatBar(QWidget):
    def __init__(self, label, color=QColor("#3a86ff"), parent=None):
        super().__init__(parent)
        self.label = label
        self.value = -60.0
        self.target = 0.0
        self.color = color
        self.setMinimumHeight(20)

    def set_value(self, val):
        self.value = val
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ddd"))
        painter.drawRect(rect)

        bar_width = (self.value + 60) / 60 * rect.width()
        bar_width = max(0, min(rect.width(), bar_width))

        painter.setBrush(self.color)
        painter.drawRect(0, 0, int(bar_width), rect.height())

        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 9))
        painter.drawText(rect.adjusted(5, 0, -5, 0), Qt.AlignLeft | Qt.AlignVCenter, f"{self.label}: {self.value:.2f} dB")

class AudioStatsWidget(QWidget):
    def __init__(self, audiosegment, lang="en", parent=None):
        super().__init__(parent)
        self.audio = audiosegment
        self.lang = lang
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.label_hint = QLabel("")
        self.label_hint.setWordWrap(True)
        self.layout.addWidget(self.label_hint)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1500)

        self.update_stats()

    def update_stats(self):
        try:
            data = np.array(self.audio.get_array_of_samples()).astype(np.float32)
            if data.ndim == 1:
                data = np.stack([data, data], axis=1)

            loudness = analyze_loudness(data)
            hint = get_loudness_hint_for_lang(loudness, target=-14.0, lang=self.lang)
            self.label_hint.setText(f"💡 {hint}")
        except Exception as e:
            self.label_hint.setText(f"⚠️ {str(e)}")
