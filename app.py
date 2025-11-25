import streamlit as st
import streamlit.components.v1 as components
import json
import os
import io
import requests
from dotenv import load_dotenv
from audio_recorder_streamlit import audio_recorder

# Fonctions de ton agent
from agent_extract import appeler_groq, extraire_json, normaliser_dates, ajouter_items_si_user_accepte

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
st.set_page_config(page_title="EaseMyDay", layout="wide", page_icon="🧠")
st.title("EaseMyDay — Assistant Intelligent 🧠")

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
    if "last_extracted" not in st.session_state:
        st.session_state.last_extracted = None

    # Historique du chat
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # AUDIO
    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_name="microphone",
        icon_size="2x"
    )

    final_input = None

    if audio_bytes:
        with st.spinner("Transcription en cours..."):
            transcribed_text = transcribe_audio_memory(audio_bytes)
            if transcribed_text:
                final_input = transcribed_text

    text_prompt = st.chat_input("Pose ta question ou donne une instruction...")
    if text_prompt:
        final_input = text_prompt

    # TRAITEMENT DU TEXTE OU AUDIO
    if final_input:

        if not st.session_state.messages or st.session_state.messages[-1]["content"] != final_input:
            st.session_state.messages.append({"role": "user", "content": final_input})
            st.chat_message("user").write(final_input)

            with st.spinner("Analyse en cours..."):
                raw = appeler_groq(final_input)
                resume, json_data = extraire_json(raw)
                json_data = normaliser_dates(json_data)

            # Sauvegarde temporaire pour plus tard
            st.session_state.last_extracted = json_data

            # --- RÉPONSE ASSISTANT (sans JSON) ---
            if resume.strip():
                response_text = f"### Résumé de l’analyse\n{resume}\n\n"
            else:
                response_text = "J’ai analysé ton message."

            if len(json_data) == 0:
                response_text += "Aucune tâche ou rendez-vous détecté."
            else:
                response_text += "Veux-tu que j’ajoute ces informations ?"

            st.session_state.messages.append({"role": "assistant", "content": response_text})
            st.chat_message("assistant").write(response_text)

    # -------------------------------------------------------
    # BOUTON D’AJOUT DES ÉLÉMENTS
    # -------------------------------------------------------
    if st.session_state.last_extracted and len(st.session_state.last_extracted) > 0:
        st.write("---")
        st.write("Souhaites-tu enregistrer ces informations ?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Oui, ajouter"):
                ajouter_items_si_user_accepte(st.session_state.last_extracted, True)
                st.success("Les éléments ont été ajoutés.")
                st.session_state.last_extracted = None

        with col2:
            if st.button("❌ Non, annuler"):
                st.session_state.last_extracted = None
                st.info("Aucun élément n’a été ajouté.")
