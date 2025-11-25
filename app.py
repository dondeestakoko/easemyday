import streamlit as st
import streamlit.components.v1 as components
import json
import os
import io
import requests
from dotenv import load_dotenv
from audio_recorder_streamlit import audio_recorder

# Nouvelles fonctions importées depuis agent_extract.py
from agent_extract import appeler_groq, extraire_json, normaliser_dates

# Chargement .env
load_dotenv()

# -------------------------------------------------------
# TRANSCRIPTION AUDIO EN MÉMOIRE
# -------------------------------------------------------
def transcribe_audio_memory(audio_bytes):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("Clé API GROQ manquante.")
        return None

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
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
# CONFIG UI
# -------------------------------------------------------
st.set_page_config(
    page_title="EaseMyDay",
    layout="wide",
    page_icon="🧠"
)

st.title("EaseMyDay — Assistant Intelligent 🧠")

# -------------------------------------------------------
# Mise en page colonnes
# -------------------------------------------------------
col_chat, col_calendar = st.columns([2, 1], gap="large")

# -------------------------------------------------------
# COLONNE DROITE : GOOGLE CALENDAR
# -------------------------------------------------------
with col_calendar:
    st.subheader(" Mon Google Agenda")
    calendar_url = "https://calendar.google.com/calendar/embed?src=ticketsdata5%40gmail.com&ctz=Europe%2FParis"
    components.iframe(src=calendar_url, height=600, scrolling=True)

# -------------------------------------------------------
# COLONNE GAUCHE : CHAT & AUDIO
# -------------------------------------------------------
with col_chat:
    st.subheader("Discussion")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Affichage historique
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # --- AUDIO ---
    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_name="microphone",
        icon_size="2x"
    )

    final_input = None

    # Si audio => transcription
    if audio_bytes:
        with st.spinner("Transcription en cours..."):
            transcribed_text = transcribe_audio_memory(audio_bytes)
            if transcribed_text:
                final_input = transcribed_text

    # Input texte classique
    text_prompt = st.chat_input("Pose ta question ou donne une instruction...")
    if text_prompt:
        final_input = text_prompt

    # Traitement commun (texte ou audio)
    if final_input:

        # Ajout message user
        if not st.session_state.messages or st.session_state.messages[-1]["content"] != final_input:
            st.session_state.messages.append({"role": "user", "content": final_input})
            st.chat_message("user").write(final_input)

            # --- APPEL AGENT EXTRACT ---
            with st.spinner("Analyse en cours..."):
                raw = appeler_groq(final_input)     # message complet : résumé + JSON
                resume, json_data = extraire_json(raw)  # extraction du résumé + JSON
                json_data = normaliser_dates(json_data)

            # --- Construction réponse assistant ---
            response_text = ""

            # 1) Résumé naturel
            if resume.strip():
                response_text += f"### Résumé de l’analyse\n{resume}\n\n"

            # 2) JSON extrait
            if len(json_data) == 0:
                response_text += "Je n’ai détecté aucune tâche ou rendez-vous spécifique."
            else:
                response_text += (
                    "### 📦 Informations extraites\n"
                    f"```json\n{json.dumps(json_data, ensure_ascii=False, indent=2)}\n```"
                )

            # Ajout réponse assistant
            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.chat_message("assistant").write(response_text)
