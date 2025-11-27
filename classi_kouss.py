import os
import json
from datetime import datetime
from dotenv import load_dotenv

# OpenAI
from openai import OpenAI, OpenAIError, APIError

# ----------------------- Configuration -----------------------
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=API_KEY)

# ----------------------- Classificateur -----------------------
def classify_with_llm(phrase, context_time):
    prompt = f"""
Tu es un assistant de planification très intelligent.
Aujourd'hui : {context_time['day']}, {context_time['date']}, {context_time['hour']}h

Analyse la phrase suivante et produis un JSON strict avec :
- "tache"
- "categorie" parmi : étude, santé, administratif, tâches quotidiennes, loisir, autre
- "priorite" parmi : haute, moyenne, faible
- "etapes" : liste d'étapes concrètes pour réaliser la tâche
- "suggestion_commencer" : action concrète à faire maintenant

Phrase : "{phrase}"

Répond UNIQUEMENT avec un JSON valide, sans texte autour.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Tu es un assistant de planification intelligent et très précis."},
                {"role": "user", "content": prompt}
            ]
        )

        texte = response.choices[0].message.content

        # Nettoyage Markdown éventuel
        texte = texte.strip().replace("```json", "").replace("```", "").strip()

        # Extraire JSON si nécessaire
        import re
        match = re.search(r"\{.*\}", texte, re.DOTALL)
        if match:
            texte = match.group(0)

        return json.loads(texte)

    except json.JSONDecodeError:
        return {"erreur": "JSON invalide renvoyé par le modèle", "texte": texte}

    except (OpenAIError, APIError) as e:
        return {"erreur": f"Erreur API : {str(e)}"}

    except Exception as e:
        return {"erreur": f"Erreur interne : {str(e)}"}

# ----------------------- Main -----------------------
def main():
    print("=== Assistant intelligent de planification ===\n")

    phrase = input("Entrez une tâche à analyser : ").strip()
    if not phrase:
        print("Aucune phrase fournie. Fin du programme.")
        return

    # Contexte date/heure
    now = datetime.now()
    context_time = {
        "day": now.strftime("%A"),
        "date": now.strftime("%d %B %Y"),
        "hour": now.hour
    }

    # Appel LLM
    resultat = classify_with_llm(phrase, context_time)

    print("\n=== Résultat JSON ===")
    print(json.dumps(resultat, indent=4, ensure_ascii=False))

if __name__ == "__main__":
    main()
