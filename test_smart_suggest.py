import json
import os
import tempfile
from unittest.mock import patch, MagicMock

from smart_suggest import smart_suggest, _summarize_extracted
# Remplace "your_module_file" par le nom réel du fichier Python


def test_smart_suggest_basic():
    # -------------------------------------------------------
    # Create a temporary JSON file with some test items
    # -------------------------------------------------------
    sample_data = [
        {"category": "to_do", "title": "Finir devoir", "priority": 2},
        {"category": "note", "title": "Info", "text": "Ceci est un test"},
        {"category": "agenda", "title": "RDV", "datetime_iso": "2025-11-28T10:00:00"}
    ]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode="w", encoding="utf-8") as tmp_file:
        json.dump(sample_data, tmp_file)
        tmp_json_path = tmp_file.name

    # Output file path
    tmp_output = tmp_json_path.replace(".json", "_out.json")

    # -------------------------------------------------------
    # Mock the LLM API response
    # -------------------------------------------------------
    fake_llm_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({"result": "ok", "items": ["A", "B", "C"]})
                }
            }
        ]
    }

    mock_post = MagicMock()
    mock_post.status_code = 200
    mock_post.json.return_value = fake_llm_response

    with patch("requests.post", return_value=mock_post):
        result = smart_suggest(json_path=tmp_json_path, output_path=tmp_output)

    # -------------------------------------------------------
    # Assertions
    # -------------------------------------------------------

    # Function returned parsed JSON
    assert "output" in result
    assert "output_file" in result
    assert result["output"]["result"] == "ok"
    assert result["output"]["items"] == ["A", "B", "C"]

    # Output file was created
    assert os.path.exists(tmp_output)

    with open(tmp_output, "r", encoding="utf-8") as f:
        out_json = json.load(f)

    assert out_json["result"] == "ok"

    # Cleanup
    os.remove(tmp_json_path)
    os.remove(tmp_output)


def test_summarize_extracted():
    data = [
        {"category": "to_do", "title": "A", "priority": 3},
        {"category": "to_do", "title": "B", "priority": 1},
        {"category": "note", "title": "Note X", "text": "Une très longue note test"},
        {"category": "agenda", "title": "RDV X", "datetime_iso": "2025-11-28T10:00:00"},
    ]

    summary = _summarize_extracted(data)

    # Tasks are ordered by priority (highest first)
    assert summary["tasks"][0]["title"] == "A"

    # Notes contain preview field
    assert "preview" in summary["notes"][0]

    # Agenda comment format
    assert "RDV X" in summary["agenda_comments"][0]
