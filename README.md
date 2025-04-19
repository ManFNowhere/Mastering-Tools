
# 🎧 Secret Silence – Audio Mastering Tool

**Secret Silence** adalah aplikasi mastering audio ringan berbasis Python dengan antarmuka modern dan dukungan multibahasa (🇬🇧 English, 🇮🇩 Bahasa Indonesia). Dirancang untuk kreator musik, podcaster, atau siapa pun yang ingin meningkatkan kualitas audio dengan cepat tanpa kompleksitas DAW.

---

## ✨ Fitur Utama

- ✅ **Mastering Otomatis** berdasarkan platform (Spotify, YouTube, Custom)
- 🎚️ **Basic EQ, Stereo Width, Saturation** – Dapat diatur sesuai kebutuhan
- 📈 **Analisis LUFS** dengan saran peningkatan atau penurunan gain
- 🎵 **Player Interaktif** dengan preview Before vs After
- 💾 Simpan hasil mastered dan metadata (`.json`)
- 🌍 Dukungan **Bahasa Indonesia & English** – Bisa diubah langsung dari UI
- 🎛️ Rekomendasi gain otomatis berdasarkan analisis loudness

---

## 📦 Instalasi

### 1. **Clone repositori**
```bash
git clone https://github.com/namamu/secret-silence.git
cd secret-silence
```

### 2. **Install dependensi**
```bash
pip install -r requirements.txt
```

#### `requirements.txt` (isi contoh)
```
pydub
numpy
pyloudnorm
soundfile
sounddevice
PySide6
scipy
Pillow
```

### 3. **Jalankan aplikasi**
```bash
python main.py
```

---

## 🚀 Cara Menggunakan

### 1. **Pilih file WAV**
Klik **Browse** dan pilih file WAV stereo yang ingin dimastering.

### 2. **Atur parameter (opsional)**
- **Additional Gain**: Tambahkan gain manual (dalam dB)
- Aktifkan checkbox:
  - ✅ Basic EQ: Penyesuaian frekuensi menengah
  - ✅ Stereo Width: Melebarkan atau menyempitkan stereo
  - ✅ Saturation: Menambahkan warna harmonik dan kompresi lembut

### 3. **Pilih Platform**
Pilih target mastering:
- 🎧 Spotify: -14 LUFS, 16-bit, 44.1kHz
- 📹 YouTube: -13 LUFS, 16-bit, 48kHz
- ⚙️ Custom: -12 LUFS, 24-bit, 44.1kHz

### 4. **Mulai Mastering**
Klik **Start Mastering**. Proses akan berjalan dan ditampilkan progresnya.

### 5. **Preview Before & After**
- Dengarkan audio sebelum dan sesudah
- Visualisasi waveform
- Saran loudness tampil otomatis

### 6. **Simpan**
Klik **Save Mastered** untuk menyimpan hasil.
- File `.wav` disimpan
- Bersamaan dengan file `metadata.json` berisi:
  - Platform, gain diterapkan, LUFS sebelum/sesudah, preset teknis

---

## 📁 Contoh Struktur Output
```
📂 output/
├── mastered_track.wav
└── mastered_track_metadata.json
```

---

## 📊 Contoh Metadata
```json
{
  "platform": "Spotify",
  "target_lufs": -14.0,
  "gain_applied": 2.4,
  "loudness_before": -16.5,
  "loudness_after": -14.0
}
```

---

## 🛠 Teknologi yang Digunakan

- **Python 3.9+**
- **PySide6** – UI modern berbasis Qt
- **pyloudnorm** – Standar LUFS loudness
- **pydub** – Manipulasi audio sederhana
- **numpy/scipy** – DSP sederhana (filter, shaping)
- **sounddevice + soundfile** – Playback & analisis
- **Pillow** – Visualisasi waveform

---

## 🌟 Kontribusi
Ingin berkontribusi? Buat PR atau laporkan issue di GitHub!

---

## 📜 Lisensi
MIT License – bebas digunakan dan dimodifikasi dengan atribusi.

---

## 🙌 Kredit
Dikembangkan dengan ❤️ oleh [YourName]  
Didukung oleh komunitas open-source audio & penggemar mastering indie.
