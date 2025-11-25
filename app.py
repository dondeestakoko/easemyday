import streamlit as st
import streamlit.components.v1 as components
import json
import os
import io # Nécessaire pour gérer le fichier en mémoire sans le sauvegarder
import requests
from dotenv import load_dotenv
from audio_recorder_streamlit import audio_recorder

# Assure-toi que ces fonctions existent bien dans ton fichier agent_extract.py
from agent_extract import call_groq, extraire_json, normaliser_dates

# Chargement des variables d'environnement
load_dotenv()

# -------------------------------------------------------
# FONCTION TRANSCRIPTION (EN MÉMOIRE)
# -------------------------------------------------------
def transcribe_audio_memory(audio_bytes):
    """Envoie les bytes audio directement à Groq sans créer de fichier sur le disque."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("Clé API GROQ manquante.")
        return None

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        # On crée un "faux" fichier en mémoire avec io.BytesIO
        # On lui donne un nom "fictif" (audio.wav) pour que l'API sache comment le lire
        file_obj = io.BytesIO(audio_bytes)
        file_obj.name = "audio.wav" 

        files = {
            "file": ("audio.wav", file_obj),
            "model": (None, "whisper-large-v3"),
            "response_format": (None, "json")
        }
        
        response = requests.post(url, headers=headers, files=files)
        
        if response.status_code == 200:
            return response.json().get("text", "")
        else:
            st.error(f"Erreur API ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        st.error(f"Erreur de transcription : {e}")
        return None

# -------------------------------------------------------
# 1. CONFIGURATION DE LA PAGE
# -------------------------------------------------------
st.set_page_config(
    page_title="EaseMyDay",
    layout="wide",
    page_icon="🧠"
)

st.title("EaseMyDay — Assistant Intelligent 🧠")

# -------------------------------------------------------
# 2. MISE EN PAGE (Colonnes)
# -------------------------------------------------------
col_chat, col_calendar = st.columns([2, 1], gap="large")

# -------------------------------------------------------
# 3. COLONNE DE DROITE : GOOGLE CALENDAR (INCHANGÉ)
# -------------------------------------------------------
with col_calendar:
    st.subheader(" Mon Google Agenda")
    calendar_url = "https://calendar.google.com/calendar/embed?src=ticketsdata5%40gmail.com&ctz=Europe%2FParis"
    components.iframe(src=calendar_url, height=600, scrolling=True)

# -------------------------------------------------------
# 4. COLONNE DE GAUCHE : CHATBOT + AUDIO
# -------------------------------------------------------
with col_chat:
    st.subheader("Discussion")

    # Initialisation de l'historique
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Affichage de l'historique des messages
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # --- ZONE AUDIO ---
    # Le recorder renvoie des bytes si un enregistrement est fait
    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_name="microphone",
        icon_size="2x"
    )

    # Variable pour stocker le texte final (soit écrit, soit transcrit)
    final_input = None

    # 1. Si on a de l'audio, on le transcrit tout de suite
    if audio_bytes:
        with st.spinner("Transcription en cours..."):
            transcribed_text = transcribe_audio_memory(audio_bytes)
            if transcribed_text:
                final_input = transcribed_text

    # 2. Input utilisateur texte (Classique)
    text_prompt = st.chat_input("Pose ta question ou donne une instruction...")
    if text_prompt:
        final_input = text_prompt

    # --- TRAITEMENT COMMUN (Audio ou Texte) ---
    if final_input:
        # A. Afficher et sauvegarder le message utilisateur
        # Pour éviter les doublons si l'audio reste en cache, on vérifie le dernier message
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != final_input:
            st.session_state.messages.append({"role": "user", "content": final_input})
            st.chat_message("user").write(final_input)

            # B. Appel de l'agent
            with st.spinner("Analyse en cours..."):
                raw = call_groq(final_input)    # Appel LLM
                data = extraire_json(raw)       # Extraction JSON
                data = normaliser_dates(data)   # Normalisation des dates

            # C. Construction de la réponse
            if len(data) == 0:
                response_text = raw if raw and "{" not in raw else "Je n’ai détecté aucune tâche ou rendez-vous spécifique."
            else:
                response_text = f"✅ **J’ai extrait les informations suivantes :**\n\n```json\n{json.dumps(data, ensure_ascii=False, indent=2)}\n```"

            # D. Afficher et sauvegarder la réponse assistant
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.chat_message("assistant").write(response_text)