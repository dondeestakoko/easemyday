from __future__ import annotations
from datetime import datetime
from typing import Optional

import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build





SCOPES = ["https://www.googleapis.com/auth/calendar"]

class GoogleCalendarClient:
    def __init__(self, credentials_path: str = "credentials.json", token_path: str = "token.json") -> None:
        self.credentials_path = credentials_path
        self.token_path = token_path
        self.service = self._build_service()

    def _build_service(self):
        creds: Optional[Credentials] = None

        # 1. Si un token existe déjà, on le recharge
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        # 2. Si pas de token OU token invalide → on relance l'auth
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Token expiré : on le rafraîchit
                creds.refresh(Request())
            else:
                # 1ère fois : on lance le flow OAuth (fenêtre de connexion Google)
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

            # On sauvegarde le nouveau token
            with open(self.token_path, "w", encoding="utf-8") as token:
                token.write(creds.to_json())

        # 3. Construire le client Google Calendar
        service = build("calendar", "v3", credentials=creds)
        return service

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        timezone: str = "Europe/Paris",
        calendar_id: str = "primary",
    ) -> dict:                         

        event_body = {
            "summary": summary,
            "description": description,
            "start": {
                "dateTime": start.isoformat(),
                "timeZone": timezone,
            },
            "end": {
                "dateTime": end.isoformat(),
                "timeZone": timezone,
            },
        }

        event = (
            self.service.events()
            .insert(calendarId=calendar_id, body=event_body)
            .execute()
        )
        return event