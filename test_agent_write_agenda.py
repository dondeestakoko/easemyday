import json
import os
import pytest
from unittest.mock import MagicMock, patch

from agent_write_agenda import create_events_from_json, INPUT_FILE


# ------------------------------------------------------------
# FIXTURE : crée un fichier JSON temporaire pour les tests
# ------------------------------------------------------------
@pytest.fixture
def agenda_json(tmp_path):
    data = [
        {
            "category": "agenda",
            "text": "Rendez-vous test 14h-16h",
            "datetime_iso": "2025-02-28T14:00:00"
        },
        {
            "category": "agenda",
            "text": "Un événement sans date",
            "datetime_iso": None
        }
    ]

    json_path = tmp_path / "extracted_items.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Patch INPUT_FILE vers notre fichier temporaire
    with patch("agent_write_agenda.INPUT_FILE", str(json_path)):
        yield


# ------------------------------------------------------------
# TEST : création d’un événement sans conflit
# ------------------------------------------------------------
@patch("agent_write_agenda.authenticate_google_calendar")
def test_create_event_no_conflict(mock_auth, agenda_json):
    # Simule service.events()
    mock_service = MagicMock()

    # Aucun événement existant → pas de conflit
    mock_service.events().list().execute.return_value = {"items": []}

    # Simule l’insertion réussie
    mock_service.events().insert().execute.return_value = {
        "summary": "Rendez-vous test 14h-16h"
    }

    mock_auth.return_value = mock_service

    result = create_events_from_json()

    assert result["created"] == 1
    assert result["skipped"] == 1  # l’item sans date est ignoré


# ------------------------------------------------------------
# TEST : conflit → aucun événement créé
# ------------------------------------------------------------
@patch("agent_write_agenda.authenticate_google_calendar")
def test_event_conflict(mock_auth, agenda_json):
    mock_service = MagicMock()

    # Simule un conflit : un événement existe déjà
    mock_service.events().list().execute.return_value = {
        "items": [{"summary": "Cours de math"}]
    }

    mock_auth.return_value = mock_service

    result = create_events_from_json()

    assert result["created"] == 0
    assert result["skipped"] == 2  # 1 conflit + 1 sans date
