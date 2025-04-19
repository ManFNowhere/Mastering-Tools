import pyloudnorm as pyln
import numpy as np


def analyze_loudness(data, sample_rate=44100):
    """
    Calculates integrated loudness (LUFS) of the given audio data.
    Ensures data is float32, stereo, and scaled correctly (from -1.0 to 1.0).
    """
    meter = pyln.Meter(sample_rate)
    if data.dtype != np.float32:
        data = data.astype(np.float32)

    # Reshape mono to stereo and normalize if needed
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)

    # If the data appears to be in int16 range, scale it
    if np.max(np.abs(data)) > 1.5:
        data = data / 32768.0

    return meter.integrated_loudness(data)

def analyze_peak_rms(data):
    """
    Calculates peak and RMS (Root Mean Square) of the audio signal.
    Returns values in dBFS.
    """
    # Pastikan float32
    data = data.astype(np.float32)

    # Pastikan stereo
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)

    # Deteksi apakah data masih dalam skala int16 atau int32 dan normalisasi
    if np.max(np.abs(data)) > 1.5:
        print("🔧 Detected int audio, normalizing to float [-1, 1]...")
        data = data / 32768.0  # Untuk int16

    # Hitung Peak dan RMS dalam dBFS
    peak = np.max(np.abs(data))
    rms = np.sqrt(np.mean(data**2))

    peak_db = 20 * np.log10(peak + 1e-12)
    rms_db = 20 * np.log10(rms + 1e-12)
    return peak_db, rms_db


def get_loudness_hint_for_lang(measured_lufs, target_lufs, lang="en"):
    diff = measured_lufs - target_lufs
    abs_diff = abs(diff)

    hints = {
        "en": {
            "perfect": "Perfect! Your audio matches the platform loudness target.",
            "too_loud": f"Your audio is too loud by {abs_diff:.2f} dB. Try reducing gain.",
            "too_soft": f"Your audio is too soft by {abs_diff:.2f} dB. Try increasing gain."
        },
        "id": {
            "perfect": "Sempurna! Audio Anda sudah sesuai target platform.",
            "too_loud": f"Audio Anda terlalu keras sebesar {abs_diff:.2f} dB. Coba kurangi gain.",
            "too_soft": f"Audio Anda terlalu pelan sebesar {abs_diff:.2f} dB. Coba tambahkan gain."
        }
    }

    if abs_diff < 1.0:
        return hints[lang]["perfect"]
    elif diff > 0:
        return hints[lang]["too_loud"]
    else:
        return hints[lang]["too_soft"]


def format_time(seconds):
    """Format detik ke dalam format mm:ss."""
    m, s = divmod(int(seconds), 60)
    return f"{m:02}:{s:02}"
