import numpy as np
import soundfile as sf

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