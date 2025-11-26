import datetime
import json
import requests
import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request  

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
OUTPUT_FILE = "./json_files/google_agenda_structured.json" # Fichier de sortie
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]

# -------------------------------------------------------------
# Chargement d’un fichier (prompts)
# -------------------------------------------------------------
def load_file(path: str) -> str:
    if not os.path.exists(path):
        return ""
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
    token_path = "./json_files/token_calendar.json" # Utilisation du même token que l'autre script
    creds_path = "./json_files/credentials.json"

    # Utilise token.json s'il existe
    try:
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    except:
        pass

    # Si pas de creds → login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                print(f"Erreur: {creds_path} introuvable.")
                return []
                
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    service = build("calendar", "v3", credentials=creds)

    # On regarde à partir de maintenant
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
# Gestion JSON Existant (Deduplication)
# -------------------------------------------------------------
def load_existing_data(filepath):
    """Charge le JSON existant ou retourne une liste vide."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def get_event_signatures(data):
    """
    Crée un set de signatures (titre + date) pour identifier les doublons.
    On se base sur les clés 'text' et 'datetime_iso' de ton format précédent,
    ou 'summary' et 'start' si le format varie.
    """
    signatures = set()
    for item in data:
        # Adaptation selon les clés que ton prompt génère habituellement
        title = item.get("text") or item.get("summary") or item.get("titre")
        date = item.get("datetime_iso") or item.get("date") or item.get("start")
        
        if title and date:
            signatures.add((title, date))
    return signatures

# -------------------------------------------------------------
# Agent principal
# -------------------------------------------------------------
def google_agenda_agent():
    # 1. Lire Google Agenda (Tout récupérer)
    google_events = fetch_google_agenda()

    if not google_events:
        print("Aucun événement trouvé sur Google Agenda.")
        return

    # 2. Charger les données locales existantes pour comparer
    existing_data = load_existing_data(OUTPUT_FILE)
    existing_signatures = get_event_signatures(existing_data)
    
    print(f" {len(existing_data)} événements déjà en base locale.")

    # 3. Filtrer : garder uniquement les NOUVEAUX événements
    events_to_process = []
    
    for e in google_events:
        summary = e.get('summary', '')
        # Récupérer la date (dateTime ou date pour toute la journée)
        start_date = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
        
        # On vérifie si ce couple (titre, date) existe déjà
        if (summary, start_date) not in existing_signatures:
            events_to_process.append(e)
        else:
            # Optionnel : décommenter pour voir ce qui est ignoré
            # print(f"  ↪ Doublon ignoré : {summary}")
            pass

    if not events_to_process:
        print(" Tous les événements récupérés existent déjà localement. Rien à faire.")
        return

    print(f" {len(events_to_process)} nouveaux événements détectés à traiter.")

    # 4. Convertir en texte brut SEULEMENT les nouveaux pour le modèle
    raw_text = ""
    for e in events_to_process:
        start = e.get("start", {}).get("dateTime", e.get("start", {}).get("date", ""))
        end = e.get("end", {}).get("dateTime", e.get("end", {}).get("date", ""))
        raw_text += f"- {e.get('summary', '')}\n"
        raw_text += f"  Début : {start}\n"
        raw_text += f"  Fin   : {end}\n"
        raw_text += f"  Lieu  : {e.get('location', '')}\n"
        raw_text += f"  Description : {e.get('description', '')}\n\n"

    # 5. Appliquer ton prompt spécialisé
    # Assure-toi que agenda_prompt.txt demande bien de retourner une LISTE JSON
    prompt_path = "./prompt/agenda_prompt.txt"
    if not os.path.exists(prompt_path):
        print(f"Erreur: Prompt {prompt_path} introuvable.")
        return

    prompt = load_file(prompt_path)
    
    print(" Envoi à Groq pour structuration...")
    json_response_str = groq_format(prompt, raw_text)

    # 6. Parsing et Fusion
    try:
        # On essaye de nettoyer le résultat si Groq ajoute du markdown ```json ... ```
        clean_json_str = json_response_str.replace("```json", "").replace("```", "").strip()
        new_structured_data = json.loads(clean_json_str)

        # Si Groq renvoie un seul objet, on le met dans une liste
        if isinstance(new_structured_data, dict):
            new_structured_data = [new_structured_data]
            
        # Fusion : Anciennes données + Nouvelles données
        final_data = existing_data + new_structured_data
        
        # 7. Sauvegarde
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)

        print(f"\n Succès ! {len(new_structured_data)} événements ajoutés.")
        print(f" Total dans {OUTPUT_FILE} : {len(final_data)} événements.")

    except json.JSONDecodeError:
        print(" Erreur : Groq n'a pas renvoyé un JSON valide.")
        print("Réponse brute :", json_response_str)
    except Exception as e:
        print(f" Erreur inattendue : {e}")

# -------------------------------------------------------------
if __name__ == "__main__":
    google_agenda_agent()