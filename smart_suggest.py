import os
import json
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "llama-3.3-70b-versatile"

# -------------------------------------------------
# Load text prompts from files
# -------------------------------------------------
def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# NOTE:
# You will create and edit these files later.
SYSTEM_PROMPT_FILE = "./prompt/smart_suggest_system.txt"
USER_PROMPT_FILE = "./prompt/smart_suggest_user.txt"

SYSTEM_PROMPT = load_prompt(SYSTEM_PROMPT_FILE)
USER_PROMPT_TEMPLATE = load_prompt(USER_PROMPT_FILE)

# -------------------------------------------------
# Helper: summarize extracted items for smarter suggestions
# -------------------------------------------------
def _summarize_extracted(data):
        """Create a concise summary of extracted items.

        The function groups items by their ``category`` and performs a few
        lightweight transformations:

        * **Tasks (to_do)** – sorted by a ``priority`` field if present (higher
            numbers first). If no priority is provided, the original order is kept.
        * **Notes** – reduced to title and a truncated preview of the text (first
            100 characters).
        * **Agenda** – turned into short human‑readable comments containing the
            title and datetime.

        The returned dictionary is JSON‑serialisable and can be injected into the
        user prompt for the LLM.
        """
        tasks = [item for item in data if item.get("category") == "to_do"]
        # Sort by priority if available; default to 0
        tasks.sort(key=lambda x: x.get("priority", 0), reverse=True)

        notes = [item for item in data if item.get("category") == "note"]
        simple_notes = [
                {
                        "title": note.get("title", "Sans titre"),
                        "preview": (note.get("text", "")[:100] + "...")
                        if len(note.get("text", "")) > 100
                        else note.get("text", ""),
                }
                for note in notes
        ]

        agenda = [item for item in data if item.get("category") == "agenda"]
        agenda_comments = [
                f"{item.get('title', 'Sans titre')} à {item.get('datetime_iso', '')}" for item in agenda
        ]

        return {
                "tasks": tasks,
                "notes": simple_notes,
                "agenda_comments": agenda_comments,
        }


# -------------------------------------------------
# Generic Smart Suggest Agent
# -------------------------------------------------
def smart_suggest(
    json_path: str = "./json_files/extracted_items.json",
    output_path: str = "./json_files/smart_suggest_output.json",
    temperature: float = 0.7,
):
    """
    General-purpose LLM agent that:
      - Reads ANY JSON file
      - Sends content into a flexible prompt
      - Asks the LLM for improved structure / organization
      - The behavior is fully controlled by the prompt files
    """
    # If the caller does not provide a path, we default to the extracted items
    # file used throughout the application. This ensures the agent always works
    # with the latest extracted data.
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    # Load JSON content
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Build a concise summary that the LLM can use to reason about tasks,
    # notes and agenda items.
    summary = _summarize_extracted(data)

    # Inject both the raw data and the summary into the user prompt. The prompt
    # files can reference ``{{JSON_DATA}}`` and ``{{SUMMARY}}`` placeholders.
    user_prompt = USER_PROMPT_TEMPLATE.replace("{{JSON_DATA}}", json.dumps(data, indent=2))
    user_prompt = user_prompt.replace("{{SUMMARY}}", json.dumps(summary, indent=2))

    # Adding a random UUID to the user prompt helps the model treat each request
    # as a distinct conversation, reducing the chance of identical completions.
    import uuid
    unique_id = str(uuid.uuid4())
    user_prompt_with_id = f"<!-- request_id: {unique_id} -->\n" + user_prompt

    payload = {
        "model": MODEL_NAME,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt_with_id}
        ],
    }

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    response = requests.post(GROQ_CHAT_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"Groq API Error: {response.text}")

    result = response.json()
    # Extract the suggestion text from the LLM response
    suggestion_text = result["choices"][0]["message"]["content"]

    # The LLM may wrap the JSON in markdown fences (```json ... ```). Clean it.
    cleaned = suggestion_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[len("```json"):]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Try to parse the cleaned string as JSON. If parsing fails, fall back to
    # storing the raw string under the key "suggestions".
    try:
        parsed = json.loads(cleaned)
    except Exception:
        parsed = {"suggestions": cleaned}

    # Write the parsed JSON to the output file.
    try:
        with open(output_path, "w", encoding="utf-8") as out_f:
            json.dump(parsed, out_f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise IOError(f"Failed to write smart suggest output to {output_path}: {e}")

    return {"output": parsed, "output_file": output_path}


if __name__ == "__main__":
    """Run a quick demonstration of the smart suggest agent.

    The original example attempted to load a non‑existent ``sample.json`` file,
    which caused a ``FileNotFoundError``. We now simply call ``smart_suggest``
    without arguments so it defaults to the ``extracted_items.json`` file used
    throughout the application. If that file is also missing, a clear error is
    raised.
    """
    # Use the default path (extracted_items.json) for the demo.
    output = smart_suggest()
    print("\n=== SMART SUGGEST OUTPUT ===\n")
    print(output)
