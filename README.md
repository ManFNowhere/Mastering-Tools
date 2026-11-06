# SS-Mastering

A lightweight desktop audio mastering application built with Python and PySide6. Designed for music creators, podcasters, and anyone who wants to bring their audio up to streaming platform standards — without the complexity of a full DAW.

---

## Features

- **Platform-aware mastering** — targets the correct LUFS for Spotify, YouTube, Apple Music, SoundCloud, TikTok, or a custom setting
- **Shelf EQ** — low shelf (200 Hz) and high shelf (8 kHz) for tonal shaping
- **Stereo Width** — M/S matrix-based width control, from mono to wide
- **Saturation** — normalized tanh waveshaper for harmonic color and density
- **True Peak Limiter** — prevents intersample clipping before export (−1 dBTP)
- **LUFS normalization** — automatically matches the target loudness of each platform
- **Before / After preview** — interactive audio player with waveform visualization
- **Auto Gain** — analyzes your file and suggests the correct gain offset
- **Multi-format export** — WAV, FLAC, or MP3 with automatic metadata JSON
- **Bilingual UI** — English and Bahasa Indonesia, switchable live

---

## Platform Targets

| Platform    | Target LUFS | Bit Depth | Sample Rate |
|-------------|-------------|-----------|-------------|
| Spotify     | −14 LUFS    | 16-bit    | 44.1 kHz    |
| YouTube     | −13 LUFS    | 16-bit    | 48 kHz      |
| Apple Music | −16 LUFS    | 24-bit    | 44.1 kHz    |
| SoundCloud  | −14 LUFS    | 16-bit    | 44.1 kHz    |
| TikTok      | −14 LUFS    | 16-bit    | 44.1 kHz    |
| Custom      | −12 LUFS    | 24-bit    | 44.1 kHz    |

---

## Installation & Setup

### Requirements
- **Python 3.9 or newer** — [python.org/downloads](https://www.python.org/downloads/)
- **FFmpeg** *(optional)* — required only for MP3 export

### Step 1 — Clone the repository

```bash
git clone https://github.com/your-username/ss-mastering.git
cd ss-mastering
```

### Step 2 — Run the setup script

```bash
python run.py
```

That's it. `run.py` will automatically:

1. Check that your Python version is 3.9 or higher
2. Create an isolated `.venv` virtual environment inside the project folder
3. Install all required packages inside that venv (nothing is installed globally on your machine)
4. Warn you if FFmpeg is missing (MP3 export won't be available without it)
5. Launch the app

> On subsequent runs, just execute `python run.py` again — it will detect the existing venv and skip the installation step, launching the app immediately.

### FFmpeg (optional — MP3 export only)

| OS      | Command                                                     |
|---------|-------------------------------------------------------------|
| macOS   | `brew install ffmpeg`                                       |
| Ubuntu  | `sudo apt install ffmpeg`                                   |
| Fedora  | `sudo dnf install ffmpeg`                                   |
| Windows | Download from [ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add to PATH |

---

## Usage Guide

### 1. Load your audio file

Click the **Browse** button and select a stereo WAV file from your computer.

> **Important:** The app requires a **stereo WAV file** as input. Mono files and other formats (MP3, FLAC) are not supported as input — convert them first using Audacity or ffmpeg:
> ```bash
> ffmpeg -i input.mp3 -ac 2 output.wav
> ```

---

### 2. Set the target platform

Use the **Platform** dropdown to select your destination:

| Choose this | When you're uploading to... |
|-------------|----------------------------|
| Spotify | Spotify |
| YouTube | YouTube or YouTube Music |
| Apple Music | Apple Music / iTunes |
| SoundCloud | SoundCloud |
| TikTok | TikTok / Reels / Shorts |
| Custom | Any target at −12 LUFS, 24-bit, 44.1 kHz |

The mastering chain will normalize your audio to that platform's loudness standard automatically.

---

### 3. Set gain (optional)

**Manual Gain:**
Type a value in dB into the **Additional Gain** field. Use positive values to make the audio louder, negative to make it quieter.

```
Example:  2.5   → adds +2.5 dB before processing
Example: -1.0   → subtracts 1 dB before processing
Example:  0.0   → no manual adjustment (default)
```

**Auto Gain (recommended):**
Click **Auto Gain** to let the tool analyze your file and calculate the exact gain needed to reach the platform's LUFS target. The result is filled into the gain field automatically.

---

### 4. Enable processing effects (optional)

Toggle any combination of these checkboxes:

| Checkbox | What it does |
|----------|-------------|
| **Enable EQ** | Applies a low shelf (200 Hz) and high shelf (8 kHz) filter — adds warmth and air to the mix |
| **Stereo Width** | Widens or narrows the stereo field using M/S processing |
| **Saturation** | Adds harmonic color and density via a tanh waveshaper |

**Fine-tuning each effect:**

Click the **⚙ Customize** button to open the processing panel. Each effect has a slider ranging from **−10 to +10**:

- **EQ** — negative values cut, positive values boost (±5 dB max shelf gain)
- **Stereo Width** — negative narrows toward mono, positive widens the stereo field
- **Saturation** — higher values add more harmonic distortion and density

Click **Save** in the popup to apply your settings.

---

### 5. Start mastering

Click **Start Mastering**. A progress bar will appear while the processing chain runs in the background:

```
normalize peak → EQ shelves → stereo width → saturation
→ dynamic compression → LUFS normalize → true peak limit
→ resample + dither to target spec
```

Processing time depends on file length and enabled effects (typically a few seconds for a 3-minute track).

---

### 6. Preview before / after

Once mastering is complete, two audio players appear:

- **Original** — your unprocessed input file
- **Mastered** — the processed output

Each player shows:
- A waveform visualization (left channel in blue, right in pink)
- A playback slider for seeking
- **▶️ Play** and **⏸ Pause** controls
- Elapsed / total time display

A **loudness hint** is shown below the preview indicating how close the result is to the platform target:
- *"Perfect! Your audio matches the platform loudness target."*
- *"Your audio is too loud by X dB. Try reducing gain."*
- *"Your audio is too soft by X dB. Try increasing gain."*

---

### 7. Save the output

Click **Save Mastered** and choose a location and format:

| Format | Notes |
|--------|-------|
| **WAV** | Lossless, recommended for archiving or further editing |
| **FLAC** | Lossless compressed, smaller file size than WAV |
| **MP3** | Lossy, requires ffmpeg installed |

A `_metadata.json` file is saved alongside the audio file with full processing details:

```json
{
  "platform": "Spotify",
  "target_lufs": -14.0,
  "gain_applied": 2.4,
  "loudness_before": -16.5,
  "loudness_after": -14.0,
  "peak_before": -1.8,
  "peak_after": -1.0,
  "rms_before": -19.2,
  "rms_after": -16.1
}
```

---

### 8. Switch language

Use the **Language** dropdown in the bottom-right corner to switch between:
- **English**
- **Bahasa Indonesia**

The change takes effect immediately without restarting the app.

---

## Building a Standalone App

To package SS-Mastering as a native desktop app (no Python required on the target machine):

```bash
# Make sure you've run run.py at least once first, then:
python build.py
```

Build output by platform:

| Platform | Output |
|----------|--------|
| macOS    | `dist/SS-Mastering.app` |
| Windows  | `dist/SS-Mastering/SS-Mastering.exe` |
| Linux    | `dist/SS-Mastering/SS-Mastering` |

**Run the built app:**

```bash
# macOS
open dist/SS-Mastering.app

# Linux
./dist/SS-Mastering/SS-Mastering

# Windows — double-click dist\SS-Mastering\SS-Mastering.exe
```

> PyInstaller builds for the **current OS only**. Run `build.py` on each platform to produce its native binary.
>
> Always distribute the entire `dist/SS-Mastering/` folder (or `.app` bundle on macOS), not just the executable file alone.

---

## Project Structure

```
ss-mastering/
├── main.py                        # Entry point
├── ui_main.py                     # Main window (MasteringApp)
├── lang.json                      # UI strings (en / id)
├── settings.json                  # User preferences (auto-created)
├── run.py                         # Setup + launcher script
├── build.py                       # Standalone app builder (PyInstaller)
├── requirements.txt               # Dependency list
└── scripts/
    ├── mastering.py               # DSP chain (EQ, width, saturation, limiter, LUFS)
    ├── presets.py                 # Platform loudness presets
    ├── utils.py                   # Loudness, peak, RMS analysis
    ├── recommender.py             # Auto gain recommendation
    ├── audio_player_widget.py     # Playback widget with waveform
    └── custom_processing_dialog.py # Customize EQ/Width/Saturation sliders
```

---

## Tech Stack

| Library       | Purpose                                 |
|---------------|-----------------------------------------|
| PySide6       | Desktop UI (Qt6)                        |
| pyloudnorm    | ITU-R BS.1770 LUFS measurement          |
| pydub         | Audio I/O and segment manipulation      |
| numpy / scipy | DSP — shelf filters, M/S matrix, limiter|
| sounddevice   | Real-time audio playback                |
| soundfile     | Audio file reading and analysis         |
| Pillow        | Waveform image rendering                |

---

## Contributing

Pull requests and issues are welcome. For major changes, open an issue first to discuss the approach.

---

## License

MIT License — free to use and modify with attribution.
