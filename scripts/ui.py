import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from scripts.preview import EmbeddedPlayer
from scripts.mastering import master_audio
from scripts.utils import check_readiness
from scripts.presets import platform_presets
import os, threading
import soundfile as sf
import numpy as np

def start_ui():
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
