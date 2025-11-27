import os
import json
import requests

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "qwen/qwen3-32b"

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
# Generic Smart Suggest Agent
# -------------------------------------------------
def smart_suggest(json_path: str):
    """
    General-purpose LLM agent that:
      - Reads ANY JSON file
      - Sends content into a flexible prompt
      - Asks the LLM for improved structure / organization
      - The behavior is fully controlled by the prompt files
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    # Load JSON content
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Inject JSON into user prompt
    user_prompt = USER_PROMPT_TEMPLATE.replace("{{JSON_DATA}}", json.dumps(data, indent=2))

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
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
    return result["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # Example usage (you can edit or remove this)
    output = smart_suggest("./json_files/sample.json")
    print("\n=== SMART SUGGEST OUTPUT ===\n")
    print(output)
