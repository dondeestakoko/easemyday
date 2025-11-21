import os
import json
import requests
from datetime import datetime
import dateparser

# -------------------------------------------------
# CONFIGURATION
# -------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL_NAME = "qwen/qwen3-32b"

SYSTEM_PROMPT_FILE = "system_prompt.txt"
USER_PROMPT_FILE = "user_prompt.txt"
OUTPUT_JSON_FILE = "extracted_items.json"

# -------------------------------------------------
# Charger les prompts
# -------------------------------------------------
def load_prompt(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

SYSTEM_PROMPT = load_prompt(SYSTEM_PROMPT_FILE)
USER_PROMPT_TEMPLATE = load_prompt(USER_PROMPT_FILE)

# -------------------------------------------------
# Appel API Groq
# -------------------------------------------------
def appeler_groq(text_brut: str):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_PROMPT_TEMPLATE.format(text=text_brut)},
        ],
        "temperature": 0.0,
        "max_tokens": 800,
    }

    r = requests.post(GROQ_CHAT_URL, headers=headers, json=payload)

    if r.status_code != 200:
        raise RuntimeError(f"Erreur API Groq {r.status_code} : {r.text}")

    return r.json()["choices"][0]["message"]["content"]

# -------------------------------------------------
# Parse JSON
# -------------------------------------------------
def extraire_json(s: str):
    s = s.strip()

    # Tentative direct
    try:
        return json.loads(s)
    except:
        pass

    # Sinon tenter entre crochets
    start = s.find("[")
    end = s.rfind("]")
    if start != -1 and end != -1:
        try:
            return json.loads(s[start:end+1])
        except:
            pass

    raise ValueError("Impossible de parser la réponse JSON :\n" + s)

# -------------------------------------------------
# Normalisation des dates
# -------------------------------------------------
def normaliser_dates(items):
    for it in items:
        raw = it.get("datetime_raw")
        iso = it.get("datetime_iso")

        if iso:
            try:
                parsed = dateparser.parse(iso)
                if parsed:
                    it["datetime_iso"] = parsed.isoformat()
            except:
                pass

        elif raw:
            parsed = dateparser.parse(raw)
            it["datetime_iso"] = parsed.isoformat() if parsed else None

        else:
            it["datetime_iso"] = None

    return items

# -------------------------------------------------
# Pipeline principal
# -------------------------------------------------
def extraire_et_sauver(text_brut: str, output=OUTPUT_JSON_FILE):
    print("[INFO] Envoi du texte à Groq...")
    contenu = appeler_groq(text_brut)

    print("[INFO] Parsing JSON...")
    items = extraire_json(contenu)

    print("[INFO] Normalisation des dates...")
    items = normaliser_dates(items)

    print("[INFO] Sauvegarde...")
    with open(output, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    print(f"[OK] {len(items)} éléments enregistrés → {output}")
    return items

# -------------------------------------------------
# Exemple d'utilisation
# -------------------------------------------------
if __name__ == "__main__":
    texte = """
    Appeler le docteur lundi à 15h.
    Acheter des bouteilles d’eau.
    Note : penser à vérifier les sauvegardes.
    Réunion d'équipe mardi prochain à 10h.
    """

    resultat = extraire_et_sauver(texte)
    print(json.dumps(resultat, indent=2, ensure_ascii=False))
