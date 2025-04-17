import tkinter as tk
import sounddevice as sd
import soundfile as sf
import threading
import io
from scripts.waveform_canvas import WaveformCanvas

class EmbeddedPlayer:
    def __init__(self, container, audiosegment, title):
        self.audio = audiosegment
        self.play_thread = None
        self.stop_flag = threading.Event()
        self.seek_flag = threading.Event()
        self.current_position = 0

        self.data, self.fs = sf.read(io.BytesIO(audiosegment.export(format="wav").read()), dtype='float32')
        self.total_duration = len(self.data) / self.fs

        self.container = container
        tk.Label(container, text=title, font=("Helvetica", 12, "bold")).pack()
        self.slider = tk.Scale(container, from_=0, to=self.total_duration, orient="horizontal", length=400, resolution=0.1, command=self.slider_seek)
        self.slider.pack(pady=2)

        # Waveform canvas
        self.waveform = WaveformCanvas(container, audiosegment)

        # Bind mouse events
        self.slider.bind("<ButtonPress-1>", self.on_slider_press)
        self.slider.bind("<ButtonRelease-1>", self.on_slider_release)

        control_frame = tk.Frame(container)
        control_frame.pack()

        self.play_button = tk.Button(control_frame, text="▶️ Play", command=self.play)
        self.play_button.grid(row=0, column=0, padx=10)
        self.stop_button = tk.Button(control_frame, text="⏹ Stop", command=self.stop)
        self.stop_button.grid(row=0, column=1, padx=10)

        self.updating_slider = True
        self.update_slider()

    def on_slider_press(self, event):
        self.seek_flag.set()

    def on_slider_release(self, event):
        self.current_position = float(self.slider.get())
        self.seek_flag.clear()
        if hasattr(self, 'waveform'):
            self.waveform.update_seek_bar(self.current_position / self.total_duration)

    def slider_seek(self, value):
        if self.seek_flag.is_set():
            self.current_position = float(value)
            if hasattr(self, 'waveform'):
                self.waveform.update_seek_bar(self.current_position / self.total_duration)

    def play(self):
        if self.play_thread and self.play_thread.is_alive():
            return

        self.stop_flag.clear()
        self.current_position = self.slider.get()

        def _play():
            try:
                with sd.OutputStream(samplerate=self.fs, channels=self.data.shape[1]) as stream:
                    i = int(self.current_position * self.fs)
                    while i < len(self.data) and not self.stop_flag.is_set():
                        if self.seek_flag.is_set():
                            i = int(self.current_position * self.fs)
                            continue
                        stream.write(self.data[i:i+1])
                        self.current_position = i / self.fs
                        i += 1
            except Exception as e:
                print("Playback error:", e)

        self.play_thread = threading.Thread(target=_play, daemon=True)
        self.play_thread.start()

    def stop(self):
        self.stop_flag.set()
        sd.stop()
        if hasattr(self, 'waveform'):
            self.waveform.reset_seek_bar()

    def update_slider(self):
        if not self.stop_flag.is_set() and not self.seek_flag.is_set():
            self.slider.set(self.current_position)
            if hasattr(self, 'waveform'):
                self.waveform.update_seek_bar(self.current_position / self.total_duration)
        self.container.after(100, self.update_slider)