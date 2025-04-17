# AudioPlayerWidget improvements and utils.py review will be applied here.

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSlider, QHBoxLayout
from PySide6.QtGui import QPixmap, QImage, QPainter, QColor
from PySide6.QtCore import Qt, QTimer
import numpy as np
import soundfile as sf
import sounddevice as sd
import threading
import io
from pydub import AudioSegment
from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt
from scripts.utils import format_time

class AudioPlayerWidget(QWidget):
    def __init__(self, audiosegment: AudioSegment, title="", parent=None):
        super().__init__(parent)
        self.audiosegment = audiosegment
        self.title = title
        self.data, self.fs = self._convert_audio(audiosegment)
        self.position = 0
        self.playing = False

        self.setMinimumHeight(200)

        self.label_title = QLabel(title)
        self.button_play = QPushButton("▶️ Play")
        self.button_pause = QPushButton("⏸ Pause")
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, int(len(self.data[0]) / self.fs))
        self.label_time = QLabel("00:00 / 00:00")

        self.button_play.clicked.connect(self.play)
        self.button_pause.clicked.connect(self.pause)
        self.slider.sliderPressed.connect(self.pause_slider_update)
        self.slider.sliderReleased.connect(self.seek_to_slider)

        self.waveform_label = QLabel()
        self.waveform_label.setPixmap(self._draw_waveform())

        layout = QVBoxLayout()
        layout.addWidget(self.label_title)
        layout.addWidget(self.waveform_label)
        layout.addWidget(self.slider)
        layout.addWidget(self.label_time)

        controls = QHBoxLayout()
        controls.addWidget(self.button_play)
        controls.addWidget(self.button_pause)
        layout.addLayout(controls)

        self.setLayout(layout)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_slider)
        self.slider_being_dragged = False

        self.duration = len(self.data[0]) / self.fs
        self.update_time_label()

    def _convert_audio(self, audiosegment):
        buf = io.BytesIO()
        audiosegment.export(buf, format="wav")
        buf.seek(0)
        data, fs = sf.read(buf, dtype='float32')
        if data.ndim == 1:
            data = np.stack([data, data], axis=1)
        return (data[:, 0], data[:, 1]), fs

    def _draw_waveform(self):
        width = 600
        height = 100
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        mid = height // 2

        step = max(1, len(self.data[0]) // width)
        left_samples = self.data[0][::step]
        right_samples = self.data[1][::step]

        for x, (l, r) in enumerate(zip(left_samples, right_samples)):
            lh = int(l * (height // 2 - 1))
            rh = int(r * (height // 2 - 1))
            draw.line([(x, mid), (x, mid - lh)], fill=(0, 128, 255))  # blue left
            draw.line([(x, mid), (x, mid + rh)], fill=(255, 0, 128))  # pink right

        return QPixmap.fromImage(ImageQt(img))

    def play(self):
        if self.playing:
            return
        self.playing = True
        self.stream = sd.OutputStream(samplerate=self.fs, channels=2, callback=self._callback)
        self.stream.start()
        self.timer.start(100)

    def pause(self):
        if hasattr(self, 'stream'):
            self.stream.stop()
            self.stream.close()
        self.playing = False
        self.timer.stop()

    def _callback(self, outdata, frames, time, status):
        if status:
            print(status)
        chunk_l = self.data[0][self.position:self.position + frames]
        chunk_r = self.data[1][self.position:self.position + frames]
        chunk = np.stack((chunk_l, chunk_r), axis=1)

        if len(chunk) < frames:
            outdata[:len(chunk)] = chunk
            outdata[len(chunk):] = 0
            self.pause()
        else:
            outdata[:] = chunk
        self.position += frames

    def update_slider(self):
        if not self.slider_being_dragged:
            self.slider.setValue(int(self.position / self.fs))
        self.update_time_label()

    def pause_slider_update(self):
        self.slider_being_dragged = True

    def seek_to_slider(self):
        self.position = int(self.slider.value() * self.fs)
        self.slider_being_dragged = False

    def update_time_label(self):
        current = self.position / self.fs
        self.label_time.setText(f"{format_time(current)} / {format_time(self.duration)}")
