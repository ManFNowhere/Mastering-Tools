import tkinter as tk
from tkinter import filedialog, messagebox
from pydub import AudioSegment, effects
import numpy as np
import soundfile as sf
import os
from tkinter import ttk
import threading
import sounddevice as sd
import io
# ----- PLATFORM TARGET PRESETS -----
platform_presets = {
    "Spotify": {"target_lufs": -14, "bit_depth": 16, "sample_rate": 44100},
    "YouTube": {"target_lufs": -13, "bit_depth": 16, "sample_rate": 48000},
    "Custom": {"target_lufs": -12, "bit_depth": 24, "sample_rate": 44100}
}

# ----- AUDIO PROCESSING FUNCTIONS -----
def analyze_loudness(audio_data):
    rms = np.sqrt(np.mean(np.square(audio_data)))
    loudness_db = 20 * np.log10(rms + 1e-9)
    return loudness_db

def check_readiness(file_path):
    try:
        data, samplerate = sf.read(file_path)
        peak_db = 20 * np.log10(np.max(np.abs(data)) + 1e-9)
        loudness = analyze_loudness(data)

        if data.ndim != 2 or data.shape[1] != 2:
            raise ValueError("File harus stereo.")
        if peak_db > -3:
            raise ValueError(f"Peak terlalu tinggi ({peak_db:.2f} dBFS). Maksimum -3 dBFS.")
        if loudness > -14:
            raise ValueError(f"Loudness terlalu keras ({loudness:.2f} LUFS). Harus lebih kecil dari -14 LUFS.")
        if loudness < -20:
            raise ValueError(f"Loudness terlalu pelan ({loudness:.2f} LUFS). Harus lebih besar dari -20 LUFS.")
        return True
    except Exception as e:
        raise ValueError(f"Pemeriksaan gagal: {e}")

# matering part
def apply_eq(audio):
    bass = audio.low_pass_filter(150)
    treble = audio.high_pass_filter(4000)
    return audio.overlay(bass).overlay(treble)

def apply_stereo_width(audio):
    left, right = audio.split_to_mono()
    widened = AudioSegment.from_mono_audiosegments(left - 1, right + 1)
    return widened

def apply_saturation(audio):
    return audio.apply_gain_stereo(-0.5, 0.5).compress_dynamic_range()

def master_audio(file_path, gain_db, use_eq, use_width, use_saturation, platform, progress_callback):
    audio = AudioSegment.from_file(file_path)
    if audio.channels != 2:
        raise ValueError("File input harus stereo.")

    progress_callback(10)
    normalized = audio.apply_gain(-audio.max_dBFS)
    progress_callback(25)

    if use_eq:
        normalized = apply_eq(normalized)
    progress_callback(45)

    if use_width:
        normalized = apply_stereo_width(normalized)
    progress_callback(60)

    if use_saturation:
        normalized = apply_saturation(normalized)
    progress_callback(75)

    final = normalized.apply_gain(gain_db)
    final = effects.compress_dynamic_range(final)
    progress_callback(90)

    preset = platform_presets[platform]
    final = final.set_frame_rate(preset["sample_rate"]).set_sample_width(preset["bit_depth"] // 8)
    progress_callback(100)

    return audio, final

# Documentation String
DOCUMENTATION = """
Cara Mixing agar Siap Digunakan:
- Export file mixdown ke WAV, 24-bit, 44.1kHz atau 48kHz
- Pastikan mix sudah final (tidak akan diubah lagi)
- Hindari limiter atau maximizer di master bus
- Sisakan headroom 3-6 dBFS (peak maksimal -3 dBFS)
- LUFS sekitar -18 s/d -15 LUFS
- Pastikan tidak ada clipping, panning seimbang, dan stereo balance jelas

Apa yang Dilakukan Mastering Tool Ini:
- Normalisasi dan optimalisasi gain
- Penambahan EQ dasar untuk memperkuat bass dan treble
- Stereo width enhancement
- Saturasi dan sedikit compression
- Konversi ke preset sesuai platform target
- Memberikan estimasi loudness dan opsi penyimpanan hasil

Catatan:
- Saat audio sedang diputar, slider belum bisa digunakan untuk lompat ke bagian tertentu. Ini akan diperbaiki di update selanjutnya.
"""

# Save documentation to txt file
def save_documentation():
    with open("mastering_tool_documentation.txt", "w") as f:
        f.write(DOCUMENTATION)

save_documentation()
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

    def slider_seek(self, value):
        if self.seek_flag.is_set():
            self.current_position = float(value)

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

    def update_slider(self):
        if not self.stop_flag.is_set() and not self.seek_flag.is_set():
            self.slider.set(self.current_position)
        self.container.after(200, self.update_slider)

# ----- GUI -----
def reset_ui():
    for widget in preview_frame.winfo_children():
        widget.destroy()
    save_btn.pack_forget()
    progress_bar['value'] = 0
    status_label.config(text="")

def browse_file():
    file_path = filedialog.askopenfilename(filetypes=[["WAV files", "*.wav"]])
    if file_path:
        reset_ui()
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)

def run_mastering():
    def task():
        try:
            root.config(cursor="watch")
            status_label.config(text="⏳ Memproses file...", fg="blue")
            root.update()
            progress_bar['value'] = 0

            file_path = file_entry.get()
            gain_db = float(gain_entry.get())
            use_eq = eq_var.get()
            use_width = width_var.get()
            use_saturation = sat_var.get()
            platform = platform_var.get()

            if not file_path:
                raise ValueError("Pilih file terlebih dahulu.")

            def update_progress(val):
                progress_bar['value'] = val
                root.update_idletasks()

            global original_audio, mastered_audio
            original_audio, mastered_audio = master_audio(file_path, gain_db, use_eq, use_width, use_saturation, platform, update_progress)

            status_label.config(text="✅ Mastering selesai! Silakan preview.", fg="green")
            EmbeddedPlayer(preview_frame, original_audio, "Preview Original")
            EmbeddedPlayer(preview_frame, mastered_audio, "Preview Mastered")
            save_btn.pack(pady=5)

        except Exception as e:
            status_label.config(text="❌ Terjadi kesalahan.", fg="red")
            messagebox.showerror("Error", str(e))
        finally:
            root.config(cursor="")
            root.update()

    threading.Thread(target=task).start()

def save_output():
    try:
        output_path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[["WAV files", "*.wav"]])
        if not output_path:
            return

        mastered_audio.export(output_path, format="wav")

        original_data = np.array(original_audio.get_array_of_samples())
        processed_data, _ = sf.read(output_path)
        before_loudness = analyze_loudness(original_data)
        after_loudness = analyze_loudness(processed_data)

        messagebox.showinfo("Selesai", f"Loudness Sebelum: {before_loudness:.2f} dB\nLoudness Sesudah: {after_loudness:.2f} dB\n\nFile disimpan di:\n{output_path}")
    except Exception as e:
        messagebox.showerror("Error", str(e))

# ----- GUI SETUP -----
root = tk.Tk()
root.title("Mastering Tool v0.7 - Secret Silence")
frame = tk.Frame(root, padx=20, pady=20)
frame.pack()

# INPUTS
tk.Label(frame, text="Pilih File WAV").grid(row=0, column=0, sticky="w")
file_entry = tk.Entry(frame, width=40)
file_entry.grid(row=0, column=1)
tk.Button(frame, text="Browse", command=browse_file).grid(row=0, column=2)

tk.Label(frame, text="Tambahan Gain (dB)").grid(row=1, column=0, sticky="w")
gain_entry = tk.Entry(frame, width=10)
gain_entry.insert(0, "0.0")
gain_entry.grid(row=1, column=1, sticky="w")

# TUNING OPTIONS
eq_var = tk.BooleanVar()
tk.Checkbutton(frame, text="Aktifkan EQ Dasar", variable=eq_var).grid(row=2, column=1, sticky="w")

width_var = tk.BooleanVar()
tk.Checkbutton(frame, text="Aktifkan Stereo Width", variable=width_var).grid(row=3, column=1, sticky="w")

sat_var = tk.BooleanVar()
tk.Checkbutton(frame, text="Aktifkan Saturation", variable=sat_var).grid(row=4, column=1, sticky="w")

# PLATFORM CHOICE
tk.Label(frame, text="Preset Distribusi").grid(row=5, column=0, sticky="w")
platform_var = tk.StringVar()
platform_menu = tk.OptionMenu(frame, platform_var, *platform_presets.keys())
platform_menu.grid(row=5, column=1, sticky="w")
platform_var.set("Spotify")

# BUTTON & STATUS
tk.Button(frame, text="Jalankan Mastering", command=run_mastering).grid(row=6, column=1, pady=10)
status_label = tk.Label(root, text="", font=("Helvetica", 24, "bold"))
status_label.pack()
progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
progress_bar.pack(pady=5)

preview_frame = tk.Frame(root)
preview_frame.pack()

save_btn = tk.Button(root, text="💾 Simpan Hasil Mastering", command=save_output)

root.mainloop()
