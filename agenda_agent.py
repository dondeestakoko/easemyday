import datetime
import json
import requests

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from google.auth.transport.requests import Request  

from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# -------------------------------------------------------------
# Chargement d’un fichier (prompts)
# -------------------------------------------------------------
def load_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# -------------------------------------------------------------
# Appel Groq + Llama
# -------------------------------------------------------------
def groq_format(prompt: str, raw_content: str) -> str:
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": raw_content},
        ],
        "temperature": 0.1
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    response = requests.post(GROQ_URL, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# -------------------------------------------------------------
# Récupération Google Agenda
# -------------------------------------------------------------
def fetch_google_agenda():
    creds = None

    # Utilise token.json s'il existe
    try:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    except:
        pass

    # Si pas de creds → login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)

    now = datetime.datetime.utcnow().isoformat() + "Z"
    print("Lecture du Google Agenda...")

    events_result = service.events().list(
        calendarId="primary",
        timeMin=now,
        maxResults=30,
        singleEvents=True,
        orderBy="startTime"
    ).execute()

    return events_result.get("items", [])

# -------------------------------------------------------------
# Agent principal
# -------------------------------------------------------------
def google_agenda_agent():
    # 1. Lire Google Agenda
    events = fetch_google_agenda()

    if not events:
        print("Aucun événement trouvé.")
        return

    # 2. Convertir en texte brut pour le modèle
    raw_text = ""
    for e in events:
        start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
        end = e.get("end", {}).get("dateTime", e.get("end", {}).get("date", ""))
        raw_text += f"- {e.get('summary', '')}\n"
        raw_text += f"  Début : {start}\n"
        raw_text += f"  Fin   : {end}\n"
        raw_text += f"  Lieu  : {e.get('location', '')}\n"
        raw_text += f"  Description : {e.get('description', '')}\n\n"

    # 3. Appliquer ton prompt spécialisé
    prompt = load_file("agenda_prompt.txt")

    json_struct = groq_format(prompt, raw_text)

    # 4. Sauvegarde
    with open("google_agenda_structured.json", "w", encoding="utf-8") as f:
        f.write(json_struct)

    print("\n📌 Résultat structuré enregistré dans : google_agenda_structured.json")

# -------------------------------------------------------------
if __name__ == "__main__":
    google_agenda_agent()
