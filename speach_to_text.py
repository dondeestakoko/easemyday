import requests

from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")


AUDIO_FILE = "voice.wav"   # audio file

url = "https://api.groq.com/openai/v1/audio/transcriptions"

headers = {
    "Authorization": f"Bearer {API_KEY}"
}

files = {
    "file": (AUDIO_FILE, open(AUDIO_FILE, "rb")),
    "model": (None, "whisper-large-v3")
}

response = requests.post(url, headers=headers, files=files)

print("TRANSCRIBED TEXT:")
print(response.json())
