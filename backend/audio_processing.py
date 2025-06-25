from scipy.io import wavfile
import noisereduce as nr
from pydub import AudioSegment
import numpy as np
import os

def process_audio(input_wav_path: str, output_mp3_name: str) -> str:
    """
    Processes an audio file:
    - Downsamples to 16kHz mono
    - Trims leading/trailing silence
    - Applies noise reduction
    - Raises the volume
    - Saves as MP3 in the 'processed' folder

    Returns the path to the processed MP3 file.
    """
    print (f"Processing audio file: {input_wav_path}")
    # convert .aac to .wav if needed
    if input_wav_path.endswith('.aac'):
        audio = AudioSegment.from_file(input_wav_path, format='aac')
        input_wav_path = input_wav_path.replace('.aac', '.wav')
        audio.export("./uploads", format='wav')
        print(f"Converted {input_wav_path} to WAV format.")
    # Read audio
    rate, data = wavfile.read(input_wav_path)
    print(f"The sample rate of the audio file is: {rate}")
    print(f"Audio shape: {data.shape}")

    # Convert to mono if stereo
    if len(data.shape) > 1:
        data_mono = data.mean(axis=1).astype(data.dtype)
    else:
        data_mono = data
    print(f"Audio mono shape: {data_mono.shape}")

    # Downsample to 16kHz if needed
    target_rate = 16000
    if rate != target_rate:
        audio_seg = AudioSegment(
            data_mono.tobytes(),
            frame_rate=rate,
            sample_width=data_mono.dtype.itemsize,
            channels=1
        )
        audio_seg = audio_seg.set_frame_rate(target_rate)
        data_mono = np.array(audio_seg.get_array_of_samples())
        rate = target_rate
        print(f"Downsampled to {rate} Hz")

    # Trim leading/trailing silence
    audio_seg = AudioSegment(
        data_mono.tobytes(),
        frame_rate=rate,
        sample_width=data_mono.dtype.itemsize,
        channels=1
    )
    # Only trim start/end silence, not internal
    def detect_leading_silence(sound, silence_threshold=-40.0, chunk_size=10):
        trim_ms = 0  # ms
        assert chunk_size > 0  # to avoid infinite loop
        while trim_ms < len(sound) and sound[trim_ms:trim_ms+chunk_size].dBFS < silence_threshold:
            trim_ms += chunk_size
        return trim_ms

    start_trim = detect_leading_silence(audio_seg)
    end_trim = detect_leading_silence(audio_seg.reverse())
    trimmed_audio = audio_seg[start_trim:len(audio_seg)-end_trim]
    data_mono = np.array(trimmed_audio.get_array_of_samples())

    # Noise reduction
    reduced_noise = nr.reduce_noise(y=data_mono, sr=rate, thresh_n_mult_nonstationary=1.5, stationary=True)

    # Raise the volume
    louder_audio = AudioSegment(
        reduced_noise.tobytes(),
        frame_rate=rate,
        sample_width=reduced_noise.dtype.itemsize,
        channels=1
    ).apply_gain(10)

    # Export as MP3
    output_mp3_path = os.path.join(processed_dir, output_mp3_name)
    louder_audio.export(output_mp3_path, format="mp3")
    print(f"Processed audio saved to {output_mp3_path}")
    return output_mp3_path