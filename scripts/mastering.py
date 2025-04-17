from pydub import AudioSegment, effects
from scripts.presets import platform_presets

def apply_eq(audio):
    print("🎚️ Applying EQ...")
    bass = audio.low_pass_filter(150)
    treble = audio.high_pass_filter(4000)
    return audio.overlay(bass).overlay(treble)

def apply_stereo_width(audio):
    print("🔊 Applying Stereo Width...")
    left, right = audio.split_to_mono()
    widened = AudioSegment.from_mono_audiosegments(left - 1, right + 1)
    return widened

def apply_saturation(audio):
    print("🔥 Applying Saturation...")
    return audio.apply_gain_stereo(-0.5, 0.5).compress_dynamic_range()

def master_audio(file_path, gain_db, use_eq, use_width, use_saturation, platform, progress_callback):
    print(f"📂 Loading audio from: {file_path}")
    audio = AudioSegment.from_file(file_path)
    if audio.channels != 2:
        raise ValueError("File input harus stereo.")

    print("🔊 Normalizing audio...")
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

    print(f"🎛️ Applying final gain: {gain_db} dB")
    final = normalized.apply_gain(gain_db)
    final = effects.compress_dynamic_range(final)
    progress_callback(90)

    preset = platform_presets[platform]
    print(f"📦 Applying platform preset: {platform} ({preset})")
    final = final.set_frame_rate(preset["sample_rate"]).set_sample_width(preset["bit_depth"] // 8)
    final = final.set_channels(2)  # Ensure output is stereo
    progress_callback(100)

    print("✅ Mastering complete.")
    return audio, final, preset