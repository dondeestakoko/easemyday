import json
import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request   # 👈 IMPORT CORRECT

# ----------------------------------------
# Google Calendar API - OAuth scopes
# ----------------------------------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ----------------------------------------
# Load JSON file
# ----------------------------------------
INPUT_FILE = "./json_files/extracted_items.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Filter items with category = "agenda"
agenda_items = [item for item in data if item.get("category") == "agenda"]

print(f" {len(agenda_items)} événements agenda trouvés.")

# ----------------------------------------
# Authenticate Google Calendar
# ----------------------------------------
creds = None
try:
    creds = Credentials.from_authorized_user_file("./json_files/token_calendar.json", SCOPES)
except:
    pass

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            "./json_files/credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)

    # Save token
    with open("./json_files/token_calendar.json", "w", encoding="utf-8") as token:
        token.write(creds.to_json())

service = build("calendar", "v3", credentials=creds)

# ----------------------------------------
# Create events in Google Calendar
# ----------------------------------------
created = 0

for item in agenda_items:
    text = item.get("text", "")
    date_iso = item.get("datetime_iso")

    if not date_iso:
        print(f" Ignoré (pas de datetime): {text}")
        continue

    # Start time
    start_time = date_iso

    # Create end time = +1 hour if missing
    dt = datetime.datetime.fromisoformat(date_iso)
    end_time = (dt + datetime.timedelta(hours=1)).isoformat()

    event = {
        "summary": text,
        "description": item.get("text", ""),
        "start": {"dateTime": start_time, "timeZone": "Europe/Paris"},
        "end": {"dateTime": end_time, "timeZone": "Europe/Paris"},
    }

    created_event = service.events().insert(
        calendarId="primary", body=event
    ).execute()

    created += 1
    print(f"✔️ Événement ajouté : {created_event.get('summary')}")

print(f"\n🎉 {created} événements ajoutés au Google Agenda !")
