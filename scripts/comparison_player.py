"""
Synchronized dual-track comparison player — yellow/black theme.
Single overlaid waveform canvas, one playback cursor, individual mute buttons.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPixmap, QFont
import numpy as np
import sounddevice as sd
import soundfile as sf
import io
from pydub import AudioSegment
from scripts.utils import format_time

WAVEFORM_RES = 1200

ORIG_COLOR  = QColor(79,  160, 255, 200)
MAST_COLOR  = QColor(245, 197,  24, 200)
BG_COLOR    = QColor(10,  10,  10)
GRID_COLOR  = QColor(255, 255, 255, 14)
CUR_COLOR   = QColor(255, 255, 255, 220)
PLAYED_FILL = QColor(245, 197,  24, 18)

STYLE_CTRL = """
QPushButton {
    background: #1A1A1A;
    color: #CCCCCC;
    border: 1px solid #2A2A2A;
    border-radius: 6px;
    padding: 7px 20px;
    font-size: 13px;
}
QPushButton:hover  { background: #252525; color: #FFFFFF; border-color: #3A3A3A; }
QPushButton:disabled { background: #111111; color: #2A2A2A; border-color: #1A1A1A; }
"""

STYLE_MUTE_OFF = """
QPushButton {
    background: #141414;
    color: #666666;
    border: 1.5px solid #2A2A2A;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover { background: #1E1E1E; color: #CCCCCC; border-color: #F5C518; }
"""

STYLE_MUTE_ON = """
QPushButton {
    background: #1E1900;
    color: #F5C518;
    border: 1.5px solid #F5C518;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton:hover { background: #2A2400; }
"""


def _seg_to_float32(seg: AudioSegment):
    buf = io.BytesIO()
    seg.export(buf, format="wav")
    buf.seek(0)
    data, fs = sf.read(buf, dtype="float32")
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    return data, int(fs)


def _precompute(data: np.ndarray, res: int):
    mono = (data[:, 0] + data[:, 1]) * 0.5
    n    = len(mono)
    pad  = (-n) % res
    if pad:
        mono = np.pad(mono, (0, pad))
    chunks = mono.reshape(res, -1)
    return chunks.min(axis=1).astype(np.float32), chunks.max(axis=1).astype(np.float32)


class ComparisonWaveformWidget(QWidget):
    seeked = Signal(float)

    def __init__(self, orig_mins, orig_maxs, mast_mins, mast_maxs, parent=None):
        super().__init__(parent)
        self._omins = orig_mins
        self._omaxs = orig_maxs
        self._mmins = mast_mins
        self._mmaxs = mast_maxs
        self._cursor   = 0.0
        self._cache    = None
        self._cache_sz = (0, 0)
        self.setMinimumHeight(160)
        self.setCursor(Qt.PointingHandCursor)

    def set_cursor(self, progress: float):
        self._cursor = max(0.0, min(1.0, progress))
        self.update()

    def _rebuild_cache(self, w, h):
        px = QPixmap(w, h)
        px.fill(BG_COLOR)
        p  = QPainter(px)
        p.setRenderHint(QPainter.Antialiasing, False)
        mid   = h * 0.5
        scale = mid * 0.90

        p.setPen(QPen(GRID_COLOR, 1))
        for frac in (0.25, 0.5, 0.75):
            y = int(h * frac)
            p.drawLine(0, y, w, y)

        def draw(mins_arr, maxs_arr, color):
            p.setPen(QPen(color, 1))
            res = len(mins_arr)
            for i in range(res):
                x  = int(i * w / res)
                y1 = int(mid - maxs_arr[i] * scale)
                y2 = int(mid - mins_arr[i] * scale)
                if y1 == y2:
                    y2 += 1
                p.drawLine(x, y1, x, y2)

        draw(self._omins, self._omaxs, ORIG_COLOR)
        draw(self._mmins, self._mmaxs, MAST_COLOR)

        f = QFont()
        f.setPointSize(9)
        f.setBold(True)
        p.setFont(f)
        p.setPen(ORIG_COLOR)
        p.drawText(10, 18, "● Original")
        p.setPen(MAST_COLOR)
        p.drawText(10, 34, "● Mastered")

        p.end()
        self._cache    = px
        self._cache_sz = (w, h)

    def paintEvent(self, event):
        w, h = self.width(), self.height()
        if w < 2 or h < 2:
            return
        if self._cache is None or self._cache_sz != (w, h):
            self._rebuild_cache(w, h)

        p = QPainter(self)
        p.drawPixmap(0, 0, self._cache)

        cx = int(self._cursor * w)
        p.fillRect(0, 0, cx, h, PLAYED_FILL)

        p.setPen(QPen(CUR_COLOR, 2))
        p.drawLine(cx, 0, cx, h)
        p.end()

    def resizeEvent(self, event):
        self._cache = None
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._emit_seek(event.x())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._emit_seek(event.x())

    def _emit_seek(self, x):
        prog = max(0.0, min(1.0, x / max(self.width(), 1)))
        self._cursor = prog
        self.update()
        self.seeked.emit(prog)


class ComparisonPlayerWidget(QWidget):
    def __init__(self, original_seg: AudioSegment, mastered_seg: AudioSegment, parent=None):
        super().__init__(parent)

        self._orig, self._fs = _seg_to_float32(original_seg)
        self._mast, _        = _seg_to_float32(mastered_seg)

        n = min(len(self._orig), len(self._mast))
        self._orig  = self._orig[:n]
        self._mast  = self._mast[:n]
        self._total = n
        self._dur   = n / self._fs

        self._pos         = 0
        self._playing     = False
        self._mute_orig   = False
        self._mute_mast   = False
        self._stream      = None
        self._reached_end = False

        om, oM = _precompute(self._orig, WAVEFORM_RES)
        mm, mM = _precompute(self._mast, WAVEFORM_RES)

        self.waveform = ComparisonWaveformWidget(om, oM, mm, mM)
        self.waveform.seeked.connect(self._on_wave_seek)

        self._seek_drag = False
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self._total)
        self.slider.setValue(0)
        self.slider.sliderPressed.connect(lambda: setattr(self, "_seek_drag", True))
        self.slider.sliderReleased.connect(self._on_slider_seek)

        dur_str = format_time(self._dur)
        self._dur_str = dur_str
        self.label_time = QLabel(f"00:00 / {dur_str}")
        self.label_time.setStyleSheet("color: #555555; font-size: 12px;")
        self.label_time.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.btn_play  = QPushButton("Play")
        self.btn_pause = QPushButton("Pause")
        self.btn_stop  = QPushButton("Stop")
        for b in (self.btn_play, self.btn_pause, self.btn_stop):
            b.setStyleSheet(STYLE_CTRL)
            b.setFixedHeight(36)
        self.btn_play.clicked.connect(self.play)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_stop.clicked.connect(self.stop)

        self.btn_mute_orig = QPushButton("Original: ON")
        self.btn_mute_mast = QPushButton("Mastered: ON")
        for b in (self.btn_mute_orig, self.btn_mute_mast):
            b.setStyleSheet(STYLE_MUTE_OFF)
            b.setFixedHeight(34)
        self.btn_mute_orig.clicked.connect(self.toggle_mute_orig)
        self.btn_mute_mast.clicked.connect(self.toggle_mute_mast)

        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)
        ctrl_row.addWidget(self.btn_play)
        ctrl_row.addWidget(self.btn_pause)
        ctrl_row.addWidget(self.btn_stop)
        ctrl_row.addStretch()
        ctrl_row.addWidget(self.label_time)

        mute_row = QHBoxLayout()
        mute_row.setSpacing(8)
        mute_row.addWidget(self.btn_mute_orig)
        mute_row.addWidget(self.btn_mute_mast)
        mute_row.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.waveform)
        layout.addWidget(self.slider)
        layout.addLayout(ctrl_row)
        layout.addLayout(mute_row)
        self.setLayout(layout)

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

    def play(self):
        if self._playing:
            return
        if self._pos >= self._total:
            self._pos = 0
        self._reached_end = False
        self._playing = True
        self._stream  = sd.OutputStream(
            samplerate=self._fs, channels=2,
            dtype="float32", callback=self._audio_cb,
        )
        self._stream.start()
        self._timer.start(60)

    def pause(self):
        self._playing = False
        self._close_stream()
        self._timer.stop()

    def stop(self):
        self._playing = False
        self._close_stream()
        self._timer.stop()
        self._pos = 0
        self._refresh_ui()

    def cleanup(self):
        self.stop()

    def toggle_mute_orig(self):
        self._mute_orig = not self._mute_orig
        if self._mute_orig:
            self.btn_mute_orig.setText("Original: MUTED")
            self.btn_mute_orig.setStyleSheet(STYLE_MUTE_ON)
        else:
            self.btn_mute_orig.setText("Original: ON")
            self.btn_mute_orig.setStyleSheet(STYLE_MUTE_OFF)

    def toggle_mute_mast(self):
        self._mute_mast = not self._mute_mast
        if self._mute_mast:
            self.btn_mute_mast.setText("Mastered: MUTED")
            self.btn_mute_mast.setStyleSheet(STYLE_MUTE_ON)
        else:
            self.btn_mute_mast.setText("Mastered: ON")
            self.btn_mute_mast.setStyleSheet(STYLE_MUTE_OFF)

    def _audio_cb(self, outdata, frames, time, status):
        pos    = self._pos
        end    = min(pos + frames, self._total)
        actual = end - pos
        outdata[:] = 0
        if actual > 0:
            both = not self._mute_orig and not self._mute_mast
            gain = 0.65 if both else 1.0
            if not self._mute_orig:
                outdata[:actual] += self._orig[pos:end] * gain
            if not self._mute_mast:
                outdata[:actual] += self._mast[pos:end] * gain
            np.clip(outdata, -1.0, 1.0, out=outdata)
        self._pos = end
        if end >= self._total:
            self._reached_end = True
            raise sd.CallbackStop()

    def _tick(self):
        if self._reached_end:
            self._reached_end = False
            self._close_stream()
            self._playing = False
            self._timer.stop()
            self._pos = 0
            self._refresh_ui()
            return
        self._refresh_ui()

    def _refresh_ui(self):
        progress = self._pos / max(self._total, 1)
        self.waveform.set_cursor(progress)
        if not self._seek_drag:
            self.slider.setValue(self._pos)
        self.label_time.setText(
            f"{format_time(self._pos / self._fs)} / {self._dur_str}"
        )

    def _on_slider_seek(self):
        self._seek_drag = False
        self._pos = self.slider.value()
        self._refresh_ui()

    def _on_wave_seek(self, progress: float):
        self._pos = int(progress * self._total)
        if not self._seek_drag:
            self.slider.setValue(self._pos)
        self.label_time.setText(
            f"{format_time(self._pos / self._fs)} / {self._dur_str}"
        )

    def _close_stream(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
