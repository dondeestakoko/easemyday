import sounddevice as sd
from scipy.io.wavfile import write

duration = 10  # seconds
sample_rate = 44100

print("🎙️ Recording...")
audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
sd.wait()
write("speech_batman.wav", sample_rate, audio)
print("Saved to speech.wav")
