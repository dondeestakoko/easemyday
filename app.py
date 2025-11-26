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
from agent_write_agenda import create_events_from_json

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
    
    # Refresh button
    if st.button("🔄 Actualiser l'agenda", key="refresh_calendar"):
        st.rerun()
    
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

    if "last_audio_bytes_hash" not in st.session_state:
        st.session_state.last_audio_bytes_hash = None

    if "last_message_id" not in st.session_state:
        st.session_state.last_message_id = None

    # Create a container for messages that we can update
    chat_container = st.container()

    # -------------------------------------------------------
    # AUDIO avec limitation de 7 secondes
    # -------------------------------------------------------
    st.subheader("🎤 Enregistrement vocal")
    col_mic, col_timer = st.columns([3, 1])
    
    with col_mic:
        audio_bytes = audio_recorder(
            text="Cliquez pour enregistrer",
            recording_color="#e8b62c",
            neutral_color="#6aa36f",
            icon_name="microphone",
            icon_size="2x"
        )
    
    with col_timer:
        st.markdown("**Max: 7s**")

    final_input = None

    if audio_bytes:
        # Create a hash of the audio to detect if it's the same audio
        audio_hash = hash(audio_bytes.tobytes() if hasattr(audio_bytes, 'tobytes') else str(audio_bytes))
        
        # Only process if it's new audio (not the same as last time)
        if audio_hash != st.session_state.last_audio_bytes_hash:
            st.session_state.last_audio_bytes_hash = audio_hash
            st.success("✅ Enregistrement reçu - Transcription en cours...")
            with st.spinner("🔄 Transcription en cours..."):
                final_input = transcribe_audio_memory(audio_bytes)

    # -------------------------------------------------------
    # TEXTE
    # -------------------------------------------------------
    text_prompt = st.chat_input("Pose ta question ou donne une instruction...")
    if text_prompt:
        final_input = text_prompt
        # Reset audio hash so next audio can be processed
        st.session_state.last_audio_bytes_hash = None

    # -------------------------------------------------------
    # TRAITEMENT MESSAGE
    # -------------------------------------------------------
    if final_input:
        # Create unique message ID to prevent duplicate processing
        message_id = hash(final_input + str(len(st.session_state.messages)))
        
        if st.session_state.last_message_id != message_id:
            st.session_state.last_message_id = message_id
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
            
            # Reset audio flag to prevent duplicate processing
            st.session_state.audio_processed = False
    
    # Display all messages in the container (after processing)
    with chat_container:
        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])
        else:
            # Message was already processed, clear the flag so next message can be processed
            if not st.session_state.pending_save:
                st.session_state.last_message_id = None

    # -------------------------------------------------------
    # OPTIONS DE SAUVEGARDE (avant le traitement des messages)
    # -------------------------------------------------------
    if st.session_state.pending_save and st.session_state.last_extracted:
        st.write("---")
        st.write("Souhaites-tu enregistrer ces informations ?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Oui, ajouter"):
                ajouter_items_si_user_accepte(st.session_state.last_extracted, True)
                st.success("Les éléments ont été ajoutés.")
                
                # Si des éléments "agenda" existent, créer les événements Google Calendar
                agenda_items = [item for item in st.session_state.last_extracted 
                               if item.get("category") == "agenda"]
                if agenda_items:
                    with st.spinner("Ajout des événements au calendrier..."):
                        result = create_events_from_json()
                        st.success(f"📅 {result['created']} événement(s) ajouté(s) au calendrier!")
                        if result['skipped'] > 0:
                            st.warning(f"⚠️ {result['skipped']} événement(s) ignoré(s) (créneau pris ou erreur)")
                
                st.session_state.pending_save = False
                st.session_state.last_extracted = None
                st.session_state.last_message_id = None  # Clear to prevent re-processing

        with col2:
            if st.button("Non, annuler"):
                st.info("Aucun élément n'a été ajouté.")
                st.session_state.pending_save = False
                st.session_state.last_extracted = None
                st.session_state.last_message_id = None  # Clear to prevent re-processing
