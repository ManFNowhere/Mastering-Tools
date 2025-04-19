from pydub import AudioSegment, effects
from scripts.presets import platform_presets
import json
import os
import numpy as np
import pyloudnorm as pyln
from scipy.signal import butter, lfilter

CUSTOM_FILE = "custom_settings.json"
DEFAULT_SETTINGS = {
    "eq": 0,
    "width": 0,
    "saturation": 0
}


def load_custom_settings():
    try:
        if os.path.exists(CUSTOM_FILE):
            with open(CUSTOM_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Failed to load custom settings: {e}")
    return DEFAULT_SETTINGS.copy()



# --- EQ section ---
def bandpass_filter(samples, sr, lowcut=150, highcut=4000, order=4):
    nyq = 0.5 * sr
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return lfilter(b, a, samples)


def apply_eq(audio: AudioSegment, amount=0):
    print("🎚️ Applying EQ...")
    if amount == 0:
        return audio

    sr = audio.frame_rate
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    if audio.channels == 2:
        samples = samples.reshape((-1, 2))
        left = bandpass_filter(samples[:, 0], sr)
        right = bandpass_filter(samples[:, 1], sr)
        filtered = np.stack([left, right], axis=1).flatten()
    else:
        filtered = bandpass_filter(samples, sr)

    filtered_segment = AudioSegment(
        filtered.astype(np.int16).tobytes(),
        frame_rate=sr,
        sample_width=audio.sample_width,
        channels=audio.channels
    )

    gain = amount * 0.5  # ±5 dB max
    return audio.overlay(filtered_segment.apply_gain(gain))


# --- Stereo Width section ---
def apply_stereo_width(audio: AudioSegment, amount=0):
    print("🔊 Applying Stereo Width...")
    if amount == 0:
        return audio

    left, right = audio.split_to_mono()
    mid = (left + right).apply_gain(-6)
    side = (left - right).apply_gain(amount)  # up to ±10 dB
    new_left = mid.overlay(side)
    new_right = mid.overlay(side.invert_phase())
    return AudioSegment.from_mono_audiosegments(new_left, new_right)


# --- Saturation section ---
def apply_saturation(audio: AudioSegment, amount=0):
    print("🔥 Applying Saturation...")
    if amount == 0:
        return audio

    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    bit_depth = audio.sample_width * 8
    max_val = float(2 ** (bit_depth - 1))

    samples = samples / (np.max(np.abs(samples)) + 1e-9)
    shaped = np.tanh(samples * amount)
    shaped *= (max_val - 1)

    return AudioSegment(
        shaped.astype(np.int16).tobytes(),
        frame_rate=audio.frame_rate,
        sample_width=audio.sample_width,
        channels=audio.channels
    )


# --- Loudness Normalization using LUFS ---
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
    print(f"🎯 Adjusting by {diff:.2f} dB to reach target LUFS")
    return audio.apply_gain(diff)


# --- Main Mastering Function ---
def master_audio(file_path, gain_db, use_eq, use_width, use_saturation, platform, progress_callback):
    print(f"📂 Loading audio from: {file_path}")
    audio = AudioSegment.from_file(file_path)
    if audio.channels != 2:
        raise ValueError("File input harus stereo.")

    progress_callback(10)
    normalized = audio.apply_gain(-audio.max_dBFS)
    progress_callback(25)

    settings = load_custom_settings()

    if use_eq:
        normalized = apply_eq(normalized, settings.get("eq", 0))
    progress_callback(45)

    if use_width:
        normalized = apply_stereo_width(normalized, settings.get("width", 0))
    progress_callback(60)

    if use_saturation:
        normalized = apply_saturation(normalized, settings.get("saturation", 0))
    progress_callback(75)

    final = normalized.apply_gain(gain_db)
    final = effects.compress_dynamic_range(final)
    progress_callback(90)

    preset = platform_presets[platform]
    final = normalize_loudness(final, preset["target_lufs"])

    print(f"🎛️ Final gain after normalization: {gain_db:.2f} dB")
    final = final.set_frame_rate(preset["sample_rate"]).set_sample_width(preset["bit_depth"] // 8)
    final = final.set_channels(2)
    progress_callback(100)

    print("✅ Mastering complete.")
    return audio, final, preset
