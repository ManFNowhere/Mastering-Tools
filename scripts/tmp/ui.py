import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from scripts.preview import EmbeddedPlayer
from scripts.mastering import master_audio
from scripts.utils import analyze_loudness
from scripts.presets import platform_presets
from scripts.tmp.preset_manager import save_preset, load_preset
from scripts.tmp.settings import load_settings, save_settings
import soundfile as sf
import numpy as np
import os, threading, io

texts = {
    "id": {
        "select_file": "Pilih File WAV",
        "gain": "Gain Tambahan (dB)",
        "eq": "EQ Dasar",
        "width": "Stereo Width",
        "sat": "Saturasi",
        "master": "Mastering",
        "processing": "Memproses",
        "preview": "Pratinjau",
        "original": "Original",
        "mastered": "Mastered",
        "save": "Simpan",
        "error": "Kesalahan",
        "done": "Selesai",
        "no_file": "Silakan pilih file terlebih dahulu.",
        "save_info": "Loudness Sebelum: {before} dB\nLoudness Sesudah: {after} dB\n\nFile disimpan di:\n{path}"
    },
    "en": {
        "select_file": "Select File WAV",
        "gain": "Additional Gain (dB)",
        "eq": "Basic EQ",
        "width": "Stereo Width",
        "sat": "Saturation",
        "master": "Mastering",
        "processing": "Processing",
        "preview": "Preview",
        "original": "Original",
        "mastered": "Mastered",
        "save": "Save",
        "error": "Error",
        "done": "Done",
        "no_file": "Please select a file first.",
        "save_info": "Loudness Before: {before} dB\nLoudness After: {after} dB\n\nFile saved at:\n{path}"
    }
}

def start_ui():
    settings = load_settings()
    current_lang = settings.get("language", "en")
    lang = texts[current_lang]

    def set_language(code):
        nonlocal lang, current_lang
        current_lang = code
        lang = texts[code]
        settings["language"] = code
        save_settings(settings)
        refresh_labels()

    def refresh_labels():
        file_label.config(text=lang["select_file"])
        gain_label.config(text=lang["gain"])
        eq_cb.config(text=lang["eq"])
        width_cb.config(text=lang["width"])
        sat_cb.config(text=lang["sat"])
        run_btn.config(text=lang["master"])
        preview_label.config(text=lang["preview"])
        save_btn.config(text=lang["save"])
        original_title.config(text=lang["original"])
        mastered_title.config(text=lang["mastered"])

    def browse_file():
        file_path = filedialog.askopenfilename(filetypes=[["WAV files", "*.wav"]])
        if file_path:
            file_entry.delete(0, tk.END)
            file_entry.insert(0, file_path)
            reset_output()

    def reset_output():
        for widget in preview_frame.winfo_children():
            widget.destroy()
        progress_bar['value'] = 0
        status_label.config(text="")
        save_btn.pack_forget()

    def run_mastering():
        def task():
            try:
                root.config(cursor="watch")
                progress_bar['value'] = 0
                status_label.config(text=lang["processing"], fg="green")
                root.update()

                file_path = file_entry.get()
                gain_db = float(gain_entry.get())
                use_eq = eq_var.get()
                use_width = width_var.get()
                use_saturation = sat_var.get()

                if not file_path:
                    raise ValueError(lang["no_file"])

                def update_progress(val):
                    progress_bar['value'] = val
                    root.update_idletasks()

                global original_audio, mastered_audio
                original_audio, mastered_audio = master_audio(
                    file_path, gain_db, use_eq, use_width, use_saturation, "Spotify", update_progress
                )

                status_label.config(text=lang["done"], fg="black")

                original_title.pack()
                EmbeddedPlayer(preview_frame, original_audio, "")
                mastered_title.pack()
                EmbeddedPlayer(preview_frame, mastered_audio, "")
                save_btn.pack(pady=10)

            except Exception as e:
                messagebox.showerror(lang["error"], str(e))
            finally:
                root.config(cursor="")

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

            messagebox.showinfo(
                lang["done"],
                lang["save_info"].format(before=before_loudness, after=after_loudness, path=output_path)
            )
        except Exception as e:
            messagebox.showerror(lang["error"], str(e))

    root = tk.Tk()
    root.title("Mastering Tool - Secret Silence")
    root.configure(bg="#e4e4e4")

    container = tk.Frame(root, bg="#e4e4e4", padx=20, pady=20)
    container.pack()

    top_frame = tk.Frame(container, bg="#e4e4e4")
    top_frame.pack(pady=5)

    file_label = tk.Label(top_frame, text=lang["select_file"], bg="#e4e4e4")
    file_label.pack(side="left")
    file_entry = tk.Entry(top_frame, width=50)
    file_entry.pack(side="left", padx=5)
    tk.Button(top_frame, text="Browse", command=browse_file).pack(side="left")

    ttk.Separator(container, orient="horizontal").pack(fill="x", pady=10)

    header = tk.Label(container, text="Mastering", font=("Helvetica", 14, "bold"), bg="#e4e4e4")
    header.pack()

    options_frame = tk.Frame(container, bg="#e4e4e4")
    options_frame.pack(pady=5)

    gain_label = tk.Label(options_frame, text=lang["gain"], bg="#e4e4e4")
    gain_label.grid(row=0, column=0)
    gain_entry = tk.Entry(options_frame, width=6)
    gain_entry.insert(0, "0.0")
    gain_entry.grid(row=0, column=1, padx=5)

    eq_var = tk.BooleanVar()
    eq_cb = tk.Checkbutton(options_frame, text=lang["eq"], variable=eq_var, bg="#e4e4e4")
    eq_cb.grid(row=0, column=2, padx=5)

    width_var = tk.BooleanVar()
    width_cb = tk.Checkbutton(options_frame, text=lang["width"], variable=width_var, bg="#e4e4e4")
    width_cb.grid(row=0, column=3, padx=5)

    sat_var = tk.BooleanVar()
    sat_cb = tk.Checkbutton(options_frame, text=lang["sat"], variable=sat_var, bg="#e4e4e4")
    sat_cb.grid(row=0, column=4, padx=5)

    run_btn = tk.Button(container, text=lang["master"], command=run_mastering)
    run_btn.pack(pady=10)

    status_label = tk.Label(container, text="", font=("Helvetica", 10), bg="#e4e4e4")
    status_label.pack()

    progress_bar = ttk.Progressbar(container, orient="horizontal", length=400, mode="determinate")
    progress_bar.pack(pady=10)

    ttk.Separator(container, orient="horizontal").pack(fill="x", pady=10)

    preview_label = tk.Label(container, text=lang["preview"], font=("Helvetica", 12, "bold"), bg="#e4e4e4")
    preview_label.pack()

    preview_frame = tk.Frame(container, bg="#e4e4e4")
    preview_frame.pack(pady=5)

    original_title = tk.Label(preview_frame, text=lang["original"], bg="#e4e4e4", font=("Helvetica", 10, "bold"))
    mastered_title = tk.Label(preview_frame, text=lang["mastered"], bg="#e4e4e4", font=("Helvetica", 10, "bold"))

    save_btn = tk.Button(container, text=lang["save"], command=save_output)

    lang_switch = tk.Frame(root, bg="#e4e4e4")
    lang_switch.pack(anchor="se", padx=10, pady=2)
    tk.Button(lang_switch, text="Id", command=lambda: set_language("id"), width=3).pack(side="left", padx=2)
    tk.Button(lang_switch, text="En", command=lambda: set_language("en"), width=3).pack(side="left", padx=2)

    root.mainloop()