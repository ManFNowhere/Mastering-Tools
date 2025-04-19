import tkinter as tk
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import soundfile as sf
import io

class WaveformCanvas:
    def __init__(self, parent, audiosegment, width=400, height=80):
        self.width = width
        self.height = height
        self.canvas = tk.Canvas(parent, width=width, height=height, bg='black', highlightthickness=0)
        self.canvas.pack()

        # Render waveform as image
        self.wave_img = self.render_waveform(audiosegment)
        self.tk_img = ImageTk.PhotoImage(self.wave_img)
        self.image_id = self.canvas.create_image(0, 0, anchor='nw', image=self.tk_img)

        # Add seek bar
        self.seek_bar = self.canvas.create_line(0, 0, 0, self.height, fill='red', width=2)

    def render_waveform(self, audiosegment):
        buf = io.BytesIO()
        audiosegment.export(buf, format='wav')
        buf.seek(0)
        data, rate = sf.read(buf)

        if data.ndim == 2:
            data = data.mean(axis=1)

        samples = data[::max(1, int(len(data)/self.width))]  # downsample
        img = Image.new('RGB', (self.width, self.height), 'black')
        draw = ImageDraw.Draw(img)
        mid = self.height // 2

        for x, s in enumerate(samples):
            h = int(s * (self.height // 2))
            draw.line([(x, mid - h), (x, mid + h)], fill='white')

        return img

    def update_seek_bar(self, progress):
        x = int(progress * self.width)
        self.canvas.coords(self.seek_bar, x, 0, x, self.height)

    def reset_seek_bar(self):
        self.update_seek_bar(0.0)

    def get_widget(self):
        return self.canvas
