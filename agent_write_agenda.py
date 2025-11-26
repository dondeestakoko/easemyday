import json
import datetime
import os.path
import sys
import re

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.discovery import Resource
from google.auth.transport.requests import Request
from typing import List, Dict, Any, Optional

# ========================================
# CONSTANTES DE CONFIGURATION GLOBALES
# ========================================

# Google Calendar API - OAuth scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Chemins de fichiers
INPUT_FILE = "./json_files/extracted_items.json"
TOKEN_PATH = "./json_files/token_calendar.json"
CREDS_PATH = "./json_files/credentials.json"

# Paramètres du calendrier
CALENDAR_ID = "primary"
TIMEZONE = "Europe/Paris"


# ========================================
# FONCTIONS UTILITAIRES
# ========================================

def extract_end_time_from_text(text: str, start_time: datetime.datetime) -> datetime.datetime:
    """
    Extrait l'heure de fin depuis le texte (ex: "16h-19h", "16h à 19h", "16h30-18h45")
    Si trouvée, retourne un datetime de fin. Sinon, retourne start_time + 1 heure.
    """
    # Patterns pour matcher les intervalles horaires
    patterns = [
        r'(\d{1,2})h(\d{0,2})\s*[-à]\s*(\d{1,2})h(\d{0,2})',  # "16h-19h", "16h30-18h45"
        r'(\d{1,2}):(\d{2})\s*[-à]\s*(\d{1,2}):(\d{2})',       # "16:00-19:00"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            groups = match.groups()
            end_hour = int(groups[2])
            # Handle empty string for minutes (when format is just "16h-19h")
            end_minute = int(groups[3]) if groups[3] else 0
            
            # Créer l'heure de fin avec la même date que start_time
            dt_end = start_time.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)
            
            # Si l'heure de fin est avant l'heure de début, c'est le jour suivant
            if dt_end <= start_time:
                dt_end += datetime.timedelta(days=1)
            
            return dt_end
    
    # Par défaut: 1 heure
    return start_time + datetime.timedelta(hours=1)


# ========================================
# FONCTIONS
# ========================================

def authenticate_google_calendar() -> Optional[Resource]:
    
    """
    Authentifie l'utilisateur avec l'API Google Calendar en utilisant 
    les constantes TOKEN_PATH, CREDS_PATH et SCOPES.

    Returns:
        Un objet de service Google Calendar API, ou None en cas d'échec critique.
    """
    creds = None

    # Tenter de charger les identifiants existants
    try:
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    except Exception as e:
        print(f"Erreur lors du chargement du jeton existant : {e}")

    # Si les identifiants ne sont pas valides ou n'existent pas
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Rafraîchir le jeton
            print("Jeton expiré, rafraîchissement...")
            creds.refresh(Request())
        else:
            # Exécuter le flux OAuth2 complet
            if not os.path.exists(CREDS_PATH):
                print(f"Fichier d'identifiants client non trouvé : {CREDS_PATH}")
                return None
            print("Démarrage du flux d'authentification OAuth...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # Sauvegarder le nouveau jeton
        with open(TOKEN_PATH, "w", encoding="utf-8") as token:
            token.write(creds.to_json())
        print(f"Jeton sauvegardé dans {TOKEN_PATH}.")

    # Construire l'objet de service
    try:
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Erreur lors de la construction du service Google Calendar : {e}")
        return None


def create_events_from_json() -> Dict[str, int]:
    """
    Lit les données du fichier INPUT_FILE, filtre les éléments "agenda",
    et crée des événements dans Google Calendar après vérification des conflits,
    en utilisant les constantes globales.

    Returns:
        Un dictionnaire contenant le nombre d'événements créés et ignorés.
    """
    # ----------------------------------------
    # 1. Authentification
    # ----------------------------------------
    service = authenticate_google_calendar()
    if service is None:
        return {"created": 0, "skipped": 0}

    # ----------------------------------------
    # 2. Chargement et filtrage des données
    # ----------------------------------------
    if not os.path.exists(INPUT_FILE):
        print(f"Fichier d'entrée non trouvé : {INPUT_FILE}")
        return {"created": 0, "skipped": 0}

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data: List[Dict[str, Any]] = json.load(f)

    # Filtrer les éléments avec category = "agenda"
    agenda_items = [item for item in data if item.get("category") == "agenda"]
    print(f"{len(agenda_items)} événements 'agenda' trouvés à traiter.")
    print("-" * 40)

    # ----------------------------------------
    # 3. Création des événements
    # ----------------------------------------
    created_count = 0
    skipped_count = 0

    for item in agenda_items:
        text: str = item.get("text", "Sans titre")
        date_iso: Optional[str] = item.get("datetime_iso")

        if not date_iso:
            print(f"-> Ignoré (pas de date): {text}")
            skipped_count += 1
            continue

        # Calculer les heures de début et de fin
        try:
            dt_start = datetime.datetime.fromisoformat(date_iso)
        except ValueError:
            print(f"| Format de date invalide pour : {text} ({date_iso})")
            skipped_count += 1
            continue

        # Correction pour les dates "naïves" : ajouter le fuseau horaire local
        if dt_start.tzinfo is None:
            dt_start = dt_start.astimezone()

        # Extraire l'heure de fin depuis le texte
        dt_end = extract_end_time_from_text(text, dt_start)

        # Convertir en chaîne avec l'offset de fuseau horaire pour l'API
        start_str = dt_start.isoformat()
        end_str = dt_end.isoformat()

        # ----------------------------------------
        # Vérification des conflits
        # ----------------------------------------
        try:
            events_result = service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=start_str,
                timeMax=end_str,
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            existing_events = events_result.get('items', [])

            if existing_events:
                # CONFLIT TROUVÉ
                collision_summary = existing_events[0].get('summary', 'Événement inconnu')
                print(f"X Créneau pris: '{text}' à {start_str}")
                print(f"    -> Conflit avec : '{collision_summary}'")
                skipped_count += 1
                continue
        
        except Exception as e:
            print(f"X Erreur lors de la vérification du conflit : {e}")
            skipped_count += 1 
            continue

        # ----------------------------------------
        # Création de l'événement
        # ----------------------------------------
        event_body = {
            "summary": text,
            "description": f"Ajouté par EaseMyDay. \nNote originale: {item.get('text', '')}",
            "start": {
                "dateTime": start_str,
                "timeZone": TIMEZONE
            },
            "end": {
                "dateTime": end_str,
                "timeZone": TIMEZONE
            },
        }

        try:
            created_event = service.events().insert(
                calendarId=CALENDAR_ID, body=event_body
            ).execute()

            created_count += 1
            print(f"V Événement ajouté : {created_event.get('summary')} ({start_str})")
        
        except Exception as e:
            print(f"X Erreur lors de l'ajout de l'événement : {e}")
            skipped_count += 1 

    print("-" * 40)
    print(f"Résumé : {created_count} ajoutés, {skipped_count} bloqués (créneau pris ou erreur).")

    return {"created": created_count, "skipped": skipped_count}


# ========================================
# EXECUTION DU SCRIPT
# ========================================
if __name__ == "__main__":
    results = create_events_from_json()