from __future__ import annotations
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os.path
import requests
from google.auth.transport.requests import Request


SCOPES = ["https://www.googleapis.com/auth/tasks"]

def get_tasks_service():
    creds = None

    if os.path.exists("./json_files/token.json"):
        creds = Credentials.from_authorized_user_file("./json_files/token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "./json_files/credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open("./json_files/token.json", "w") as token:
            token.write(creds.to_json())

    service = build("tasks", "v1", credentials=creds)
    return service

if __name__ == "__main__":
    service = get_tasks_service()
    # Example: List the first 10 task lists
    results = service.tasklists().list(maxResults=10).execute()
    items = results.get("items", [])

    if not items:
        print("No task lists found.")
    else:
        print("Task lists:")
        for item in items:
            print(f"{item['title']} ({item['id']})")