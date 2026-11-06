from pydub import AudioSegment, effects
from scripts.presets import platform_presets
import json
import os
import numpy as np
import pyloudnorm as pyln
from scipy.signal import butter, sosfilt
from scipy.ndimage import minimum_filter1d, uniform_filter1d

CUSTOM_FILE = "custom_settings.json"
DEFAULT_SETTINGS = {"eq": 0, "width": 0, "saturation": 0}


def load_custom_settings():
    try:
        if os.path.exists(CUSTOM_FILE):
            with open(CUSTOM_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load custom settings: {e}")
    return DEFAULT_SETTINGS.copy()


# --- EQ: low shelf + high shelf ---
def _shelf_filter(samples, sr, cutoff, gain_db, shelf_type):
    nyq = 0.5 * sr
    fc = min(cutoff / nyq, 0.99)
    sos = butter(2, fc, btype=shelf_type, output="sos")
    freq_band = sosfilt(sos, samples)
    gain_linear = 10 ** (gain_db / 20) - 1
    return samples + freq_band * gain_linear


def apply_eq(audio: AudioSegment, amount=0):
    print("🎚️ Applying EQ (shelf)...")
    if amount == 0:
        return audio

    sr = audio.frame_rate
    gain_db = amount * 0.5  # slider ±10 → ±5 dB

    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    bit_depth = audio.sample_width * 8
    max_val = float(2 ** (bit_depth - 1))
    samples_norm = samples / max_val

    stereo = samples_norm.reshape((-1, 2))
    out = np.zeros_like(stereo)

    for ch in range(2):
        s = stereo[:, ch]
        s = _shelf_filter(s, sr, 200, gain_db, "low")
        s = _shelf_filter(s, sr, 8000, gain_db, "high")
        out[:, ch] = s

    out_clipped = np.clip(out * max_val, -max_val, max_val - 1).astype(np.int16)
    return AudioSegment(
        out_clipped.flatten().tobytes(),
        frame_rate=sr,
        sample_width=audio.sample_width,
        channels=2,
    )


# --- Stereo Width: proper M/S matrix ---
def apply_stereo_width(audio: AudioSegment, amount=0):
    print("🔊 Applying Stereo Width (M/S)...")
    if amount == 0:
        return audio

    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    bit_depth = audio.sample_width * 8
    max_val = float(2 ** (bit_depth - 1))
    samples_norm = samples / max_val

    stereo = samples_norm.reshape((-1, 2))
    mid  = (stereo[:, 0] + stereo[:, 1]) * 0.5
    side = (stereo[:, 0] - stereo[:, 1]) * 0.5

    width_factor = 10 ** (amount / 20)
    side = side * width_factor

    left  = np.clip(mid + side, -1.0, 1.0)
    right = np.clip(mid - side, -1.0, 1.0)

    result = np.stack([left, right], axis=1) * (max_val - 1)
    return AudioSegment(
        result.flatten().astype(np.int16).tobytes(),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=2,
    )


# --- Saturation: normalized tanh ---
def apply_saturation(audio: AudioSegment, amount=0):
    print("🔥 Applying Saturation...")
    if amount == 0:
        return audio

    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    bit_depth = audio.sample_width * 8
    max_val = float(2 ** (bit_depth - 1))
    samples_norm = samples / max_val

    # Map 1–10 → drive 1.0–5.0; negative → near-bypass
    drive = 1.0 + max(amount, 0) / 10.0 * 4.0 if amount > 0 else 1.0
    normalizer = np.tanh(drive) + 1e-9
    shaped = np.tanh(samples_norm * drive) / normalizer

    result = np.clip(shaped * (max_val - 1), -max_val, max_val - 1).astype(np.int16)
    return AudioSegment(
        result.tobytes(),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=audio.channels,
    )


# --- True Peak Limiter ---
def apply_limiter(audio: AudioSegment, threshold_db=-1.0):
    print(f"🛑 Applying Limiter (threshold: {threshold_db} dBTP)...")

    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    bit_depth = audio.sample_width * 8
    max_val = float(2 ** (bit_depth - 1))
    samples_norm = samples / max_val

    stereo = samples_norm.reshape((-1, 2))
    peak_per_sample = np.max(np.abs(stereo), axis=1)

    threshold = 10 ** (threshold_db / 20)
    gain_needed = np.minimum(1.0, threshold / (peak_per_sample + 1e-9))

    fs = audio.frame_rate
    lookahead = max(1, int(0.005 * fs))   # 5ms attack window
    release_w = max(1, int(0.1 * fs))     # 100ms release smoothing

    gain_attack = minimum_filter1d(gain_needed, size=lookahead)
    gain_smooth = uniform_filter1d(gain_attack, size=release_w)

    g = np.stack([gain_smooth, gain_smooth], axis=1).flatten()
    limited = np.clip(samples_norm * g, -1.0, 1.0)

    return AudioSegment(
        (limited * (max_val - 1)).astype(np.int16).tobytes(),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=audio.channels,
    )


# --- Loudness Normalization (LUFS) ---
def normalize_loudness(audio: AudioSegment, target_lufs: float):
    print("📏 Normalizing loudness to target LUFS...")

    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    bit_depth = audio.sample_width * 8
    max_val = float(2 ** (bit_depth - 1))
    samples /= max_val

    if audio.channels == 1:
        samples = np.stack([samples, samples], axis=1)
    elif audio.channels == 2:
        samples = samples.reshape((-1, 2))

    meter = pyln.Meter(audio.frame_rate)
    loudness = meter.integrated_loudness(samples)
    diff = target_lufs - loudness
    print(f"🎯 Adjusting {diff:+.2f} dB to reach {target_lufs} LUFS")
    return audio.apply_gain(diff)


# --- Main Mastering Function ---
def master_audio(file_path, gain_db, use_eq, use_width, use_saturation, platform, progress_callback):
    print(f"📂 Loading audio from: {file_path}")
    audio = AudioSegment.from_file(file_path)
    if audio.channels != 2:
        raise ValueError("Input file must be stereo (2 channels).")

    progress_callback(10)
    normalized = audio.apply_gain(-audio.max_dBFS)
    progress_callback(20)

    settings = load_custom_settings()

    if use_eq:
        normalized = apply_eq(normalized, settings.get("eq", 0))
    progress_callback(35)

    if use_width:
        normalized = apply_stereo_width(normalized, settings.get("width", 0))
    progress_callback(50)

    if use_saturation:
        normalized = apply_saturation(normalized, settings.get("saturation", 0))
    progress_callback(65)

    final = normalized.apply_gain(gain_db)
    final = effects.compress_dynamic_range(final)
    progress_callback(75)

    preset = platform_presets[platform]
    final = normalize_loudness(final, preset["target_lufs"])
    progress_callback(88)

    final = apply_limiter(final, threshold_db=-1.0)
    progress_callback(94)

    final = final.set_frame_rate(preset["sample_rate"]).set_sample_width(preset["bit_depth"] // 8)
    final = final.set_channels(2)
    progress_callback(100)

    print("✅ Mastering complete.")
    return audio, final, preset
