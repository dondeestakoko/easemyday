import streamlit as st
import streamlit.components.v1 as components
import json
import os
import io
import requests
from dotenv import load_dotenv
from audio_recorder_streamlit import audio_recorder

# Fonctions de ton agent
from agent_extract import (
    appeler_groq,
    extraire_message_et_items,
    normaliser_dates,
    ajouter_items_si_user_accepte
)

# Chargement .env
load_dotenv()

# -------------------------------------------------------
# TRANSCRIPTION AUDIO
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
# UI
# -------------------------------------------------------
st.set_page_config(page_title="EaseMyDay", layout="wide", page_icon="🧠")
st.title("EaseMyDay — Assistant Intelligent 🧠")

col_chat, col_calendar = st.columns([2, 1], gap="large")

# -------------------------------------------------------
# GOOGLE CALENDAR
# -------------------------------------------------------
with col_calendar:
    st.subheader(" Mon Google Agenda")
    calendar_url = "https://calendar.google.com/calendar/embed?src=lawficenloki%40gmail.com&ctz=Europe%2FParis"
    components.iframe(src=calendar_url, height=600, scrolling=True)


# -------------------------------------------------------
# CHAT
# -------------------------------------------------------
with col_chat:
    st.subheader("Discussion")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_extracted" not in st.session_state:
        st.session_state.last_extracted = None

    if "pending_save" not in st.session_state:
        st.session_state.pending_save = False

    # ⛔ IMPORTANT : flag pour empêcher la boucle audio
    if "audio_processed" not in st.session_state:
        st.session_state.audio_processed = False

    # Display messages
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).write(msg["content"])

    # -------------------------------------------------------
    # AUDIO (corrigé)
    # -------------------------------------------------------
    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_name="microphone",
        icon_size="2x"
    )

    final_input = None

    if audio_bytes and not st.session_state.audio_processed:
        with st.spinner("Transcription en cours..."):
            final_input = transcribe_audio_memory(audio_bytes)
        st.session_state.audio_processed = True   # ⛔ bloque boucle audio

    # -------------------------------------------------------
    # TEXTE
    # -------------------------------------------------------
    text_prompt = st.chat_input("Pose ta question ou donne une instruction...")
    if text_prompt:
        final_input = text_prompt
        st.session_state.audio_processed = False  # prêt pour nouveau message audio

    # -------------------------------------------------------
    # TRAITEMENT MESSAGE
    # -------------------------------------------------------
    if final_input:

        st.session_state.messages.append({"role": "user", "content": final_input})

        with st.spinner("Analyse en cours..."):
            raw = appeler_groq(final_input)
            message_user, json_data = extraire_message_et_items(raw)
            json_data = normaliser_dates(json_data)

        st.session_state.last_extracted = json_data
        
        # Détecter si un vrai item existe
        has_extractable_items = (
            isinstance(json_data, list)
            and any(
                item.get("category") not in [None, ""] and 
                item.get("text") not in [None, ""]
                for item in json_data
            )
        )
        
        response_text = message_user

        if has_extractable_items:
            response_text += "\n\nSouhaites-tu que je les ajoute ?"
            st.session_state.pending_save = True
        else:
            st.session_state.pending_save = False
            response_text += "\n\nAucun élément à enregistrer."

        st.session_state.messages.append({"role": "assistant", "content": response_text})
        st.rerun()

    # -------------------------------------------------------
    # OPTIONS DE SAUVEGARDE
    # -------------------------------------------------------
    if st.session_state.pending_save and st.session_state.last_extracted:
        st.write("---")
        st.write("Souhaites-tu enregistrer ces informations ?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Oui, ajouter"):
                ajouter_items_si_user_accepte(st.session_state.last_extracted, True)
                st.success("Les éléments ont été ajoutés.")
                st.session_state.pending_save = False
                st.session_state.last_extracted = None
                st.rerun()

        with col2:
            if st.button("❌ Non, annuler"):
                st.info("Aucun élément n'a été ajouté.")
                st.session_state.pending_save = False
                st.session_state.last_extracted = None
                st.rerun()
