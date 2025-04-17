import numpy as np
import soundfile as sf
from pydub import AudioSegment
from scripts.utils import analyze_loudness
from scripts.presets import platform_presets

def recommend_gain(file_path, platform_name):
    # Load the audio file
    audio = AudioSegment.from_file(file_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    # Normalize sample based on bit depth
    bit_depth = audio.sample_width * 8  # e.g., 2 bytes = 16 bits
    max_val = float(2 ** (bit_depth - 1))
    samples /= max_val

    # Ensure stereo format
    if audio.channels == 1:
        samples = np.stack([samples, samples], axis=1)
    elif audio.channels == 2:
        samples = samples.reshape((-1, 2))

    # Analyze loudness
    current_lufs = analyze_loudness(samples)

    # Get platform target
    preset = platform_presets.get(platform_name, platform_presets["Spotify"])
    target_lufs = preset["target_lufs"]

    # Calculate recommended gain
    recommended_gain = target_lufs - current_lufs

    return {
        "current_lufs": current_lufs,
        "target_lufs": target_lufs,
        "recommended_gain": recommended_gain
    }