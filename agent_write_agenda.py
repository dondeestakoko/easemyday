import json
import datetime
import os.path

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

# ----------------------------------------
# Google Calendar API - OAuth scopes
# ----------------------------------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ----------------------------------------
# Load JSON file
# ----------------------------------------
INPUT_FILE = "./json_files/extracted_items.json"

# Check if file exists to avoid crash
if not os.path.exists(INPUT_FILE):
    print(f"File {INPUT_FILE} not found.")
    exit()

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Filter items with category = "agenda"
agenda_items = [item for item in data if item.get("category") == "agenda"]

print(f"🔍 {len(agenda_items)} événements agenda trouvés à traiter.")

# ----------------------------------------
# Authenticate Google Calendar
# ----------------------------------------
creds = None
token_path = "./json_files/token_calendar.json"
creds_path = "./json_files/credentials.json"

try:
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
except Exception as e:
    print(f"Error loading token: {e}")

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        if not os.path.exists(creds_path):
             print("Credentials file not found.")
             exit()
        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
        creds = flow.run_local_server(port=0)

    # Save token
    with open(token_path, "w", encoding="utf-8") as token:
        token.write(creds.to_json())

service = build("calendar", "v3", credentials=creds)

# ----------------------------------------
# Create events in Google Calendar
# ----------------------------------------
created_count = 0
skipped_count = 0

print("----------------------------------------")

for item in agenda_items:
    text = item.get("text", "Sans titre")
    date_iso = item.get("datetime_iso")

    if not date_iso:
        print(f"⚠️ Ignoré (pas de date): {text}")
        continue

    # 1. Calculate Start and End times
    try:
        dt_start = datetime.datetime.fromisoformat(date_iso)
    except ValueError:
        print(f"⚠️ Format de date invalide pour : {text} ({date_iso})")
        continue

    # --- FIX CRITIQUE POUR L'ERREUR 400 ---
    # L'API Google 'list' exige un offset timezone (ex: +01:00).
    # Si la date est 'naïve' (sans info de fuseau), on lui ajoute le fuseau local.
    if dt_start.tzinfo is None:
        dt_start = dt_start.astimezone() 
    # --------------------------------------

    # Default duration: 1 hour
    dt_end = dt_start + datetime.timedelta(hours=1)

    # Convert back to string for the API (Maintenant avec offset !)
    start_str = dt_start.isoformat()
    end_str = dt_end.isoformat()

    # ----------------------------------------
    # 2. CONFLICT CHECK (La vérification)
    # ----------------------------------------
    try:
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_str,
            timeMax=end_str,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        existing_events = events_result.get('items', [])

        if existing_events:
            # CONFLICT FOUND
            collision_summary = existing_events[0]['summary']
            print(f"❌ Space is taken: '{text}' at {start_str}")
            print(f"   ↳ Conflict with: '{collision_summary}'")
            skipped_count += 1
            continue # Skip to the next item in loop

    except Exception as e:
        print(f"⚠️ Erreur lors de la vérification du conflit : {e}")
        # En cas d'erreur de vérification, on peut choisir de continuer ou d'arrêter.
        # Ici on continue pour essayer d'insérer quand même ou passer au suivant.
        continue

    # ----------------------------------------
    # 3. If no conflict, create the event
    # ----------------------------------------
    event_body = {
        "summary": text,
        "description": f"Ajouté par EaseMyDay. \nNote originale: {item.get('text', '')}",
        "start": {
            "dateTime": start_str,
            # Le timeZone est moins critique ici car start_str a maintenant un offset,
            # mais on le garde pour la cohérence de l'affichage dans Google Agenda.
            "timeZone": "Europe/Paris" 
        },
        "end": {
            "dateTime": end_str,
            "timeZone": "Europe/Paris"
        },
    }

    try:
        created_event = service.events().insert(
            calendarId="primary", body=event_body
        ).execute()

        created_count += 1
        print(f"✔️ Événement ajouté : {created_event.get('summary')} ({start_str})")
    
    except Exception as e:
        print(f"⚠️ Error adding event: {e}")

print("----------------------------------------")
print(f"🎉 Résumé : {created_count} ajoutés, {skipped_count} bloqués (créneau pris).")