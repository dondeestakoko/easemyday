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
MODEL_NAME = "llama-3.1-8b-instant"

SYSTEM_PROMPT_FILE = "./prompt/system_prompt.txt"
USER_PROMPT_FILE = "./prompt/user_prompt.txt"
OUTPUT_JSON_FILE = "./json_files/extracted_items.json"

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
        "max_tokens": 1000,
    }

    r = requests.post(GROQ_CHAT_URL, headers=headers, json=payload)

    if r.status_code != 200:
        raise RuntimeError(f"Erreur API Groq {r.status_code} : {r.text}")

    return r.json()["choices"][0]["message"]["content"]

# -------------------------------------------------
# EXTRACTION RÉSUMÉ + JSON
# -------------------------------------------------
def extraire_json(texte_modele: str):
    texte = texte_modele.strip()

    start = texte.find("[")
    end = texte.rfind("]")

    if start == -1 or end == -1:
        raise ValueError("Aucun JSON trouvé dans la réponse :\n" + texte_modele)

    resume = texte[:start].strip()
    json_part = texte[start:end+1].strip()

    try:
        items = json.loads(json_part)
    except Exception as e:
        raise ValueError("Erreur parsing JSON :\n" + json_part) from e

    return resume, items

# -------------------------------------------------
# Normalisation des dates
# -------------------------------------------------
def normaliser_dates(items):
    for it in items:
        raw = it.get("datetime_raw")
        iso = it.get("datetime_iso")

        if iso:
            parsed = dateparser.parse(iso)
            if parsed:
                it["datetime_iso"] = parsed.isoformat()

        elif raw:
            parsed = dateparser.parse(raw)
            it["datetime_iso"] = parsed.isoformat() if parsed else None

        else:
            it["datetime_iso"] = None

    return items

# -------------------------------------------------
# Sauvegarde conditionnelle
# -------------------------------------------------
def ajouter_items_si_user_accepte(items, accept: bool, output=OUTPUT_JSON_FILE):
    """
    Ajoute les items SI ET SEULEMENT SI l'utilisateur approuve.
    """
    if not accept:
        print("[INFO] L'utilisateur n'a pas validé. Aucun élément ajouté.")
        return False

    # Charger l'existant
    if os.path.exists(output):
        with open(output, "r", encoding="utf-8") as f:
            existants = json.load(f)
    else:
        existants = []

    # Ajouter
    existants.extend(items)

    with open(output, "w", encoding="utf-8") as f:
        json.dump(existants, f, indent=2, ensure_ascii=False)

    print(f"[OK] {len(items)} élément(s) ajouté(s) → {output}")
    return True

# -------------------------------------------------
# Pipeline principal (ne sauvegarde plus)
# -------------------------------------------------
def extraire(text_brut: str):
    print("[INFO] Analyse en cours...")
    contenu = appeler_groq(text_brut)

    message, items = extraire_message_et_items(contenu)
    items = normaliser_dates(items)

    return message, items


def extraire_message_et_items(texte_modele: str):
    """
    Le modèle renvoie :
    1) Un message naturel destiné à l'utilisateur
    2) Un tableau JSON d'items extraits
    """

    texte = texte_modele.strip()

    # Localiser le JSON
    start = texte.find("[")
    end = texte.rfind("]")

    if start == -1 or end == -1:
        raise ValueError("Aucun JSON trouvé dans la réponse :\n" + texte_modele)

    message_utilisateur = texte[:start].strip()
    json_part = texte[start:end+1].strip()

    try:
        items = json.loads(json_part)
    except Exception as e:
        raise ValueError("Erreur parsing JSON :\n" + json_part) from e

    return message_utilisateur, items


# -------------------------------------------------
# Exemple d'utilisation
# -------------------------------------------------
if __name__ == "__main__":
    texte = """
    Appeler le docteur lundi à 15h.
    Acheter des bouteilles d’eau.
    Réunion d'équipe mardi prochain à 10h.
    """

    resume, resultat = extraire(texte)

    print("\n--- RÉSUMÉ ---\n")
    print(resume)

    print("\n--- EXTRAITS ---\n")
    print(json.dumps(resultat, indent=2, ensure_ascii=False))

    # Simulation : l'utilisateur confirme
    user_accepts = True

    ajouter_items_si_user_accepte(resultat, user_accepts)
