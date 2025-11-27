import streamlit as st
import streamlit.components.v1 as components
import json
import os
import io
import requests
from dotenv import load_dotenv
from audio_recorder_streamlit import audio_recorder
from datetime import datetime, timezone
import uuid
import json

# Fonctions de ton agent
from agent_extract import (
    appeler_groq,
    extraire_message_et_items,
    normaliser_dates,
    ajouter_items_si_user_accepte
)
from agent_write_agenda import create_events_from_json
# Import the agenda synchronization function
from agenda_agent import google_agenda_agent
from agent_task import EaseTasksAgent
from get_tasks_service import get_tasks_service
# Import the smart suggestion function
from smart_suggest import smart_suggest

# -------------------------------------------------
# NOTE HELPERS (local JSON storage in ./json_files)
# -------------------------------------------------
NOTES_JSON = "./json_files/notes.json"

def load_notes():
    """Load notes from the JSON file (creates it if missing)."""
    if not os.path.exists(NOTES_JSON):
        with open(NOTES_JSON, "w", encoding="utf-8") as f:
            json.dump([], f)
        return []
    with open(NOTES_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

def save_notes(notes):
    """Write the notes list back to the JSON file."""
    with open(NOTES_JSON, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)

def add_notes_to_local(json_data):
    """Create local notes from extracted items (category == 'note')."""
    notes = load_notes()
    created_count = 0
    for item in json_data:
        if item.get("category") == "note":
            note = {
                "id": str(uuid.uuid4()),
                "title": item.get("title", "Sans titre"),
                "text": item.get("text", ""),
                "datetime": item.get("datetime_iso", ""),
                "created_at": datetime.now().isoformat(),
                "archived": False,
            }
            notes.append(note)
            created_count += 1
    save_notes(notes)
    # Return a summary similar to other add_* functions
    return {"created": created_count, "skipped": 0}
    # Also clear the extracted items file to avoid re‑processing stale data
    try:
        with open("./json_files/extracted_items.json", "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def delete_note(note_id):
    """Remove a note by its UUID."""
    notes = load_notes()
    notes = [n for n in notes if n["id"] != note_id]
    save_notes(notes)

# Chargement .env
load_dotenv()

# -------------------------------------------------------
# FONCTIONS UTILITAIRES
# -------------------------------------------------------
def get_google_tasks():
    """Récupère les tâches de Google Tasks"""
    try:
        service = get_tasks_service()
        tasklists = service.tasklists().list(maxResults=10).execute()
        task_list_items = tasklists.get("items", [])
        
        all_tasks = []
        for tasklist in task_list_items:
            tasks = service.tasks().list(tasklist=tasklist["id"], maxResults=20).execute()
            task_items = tasks.get("items", [])
            for task in task_items:
                all_tasks.append({
                    "title": task.get("title", "Sans titre"),
                    "status": task.get("status", "needsAction"),
                    "list": tasklist.get("title", "Sans nom"),
                    "list_id": tasklist.get("id"),
                    "task_id": task.get("id")
                })
        return all_tasks
    except Exception as e:
        st.error(f"Erreur lors de la récupération des tâches: {e}")
        return []


def add_tasks_to_google(json_data):
    """Ajoute les tâches de catégorie 'to_do' à Google Tasks"""
    try:
        agent = EaseTasksAgent()
        tasklists = agent.list_tasklists()
        
        if not tasklists:
            st.warning("Aucune liste de tâches trouvée dans Google Tasks")
            return {"created": 0, "skipped": 0}
        
        # Utiliser la première liste de tâches
        default_tasklist = tasklists[0]["id"]
        
        created_count = 0
        skipped_count = 0
        
        for item in json_data:
            if item.get("category") == "to_do":
                title = item.get("text", "Sans titre")
                due_date = item.get("datetime_iso")
                notes = item.get("datetime_raw")
                
                try:
                    # Convertir la date ISO si elle existe
                    due_datetime = None
                    if due_date:
                        try:
                            due_datetime = datetime.fromisoformat(due_date)
                        except Exception:
                            # Fallback: try adding UTC offset
                            due_datetime = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                    
                    # Ensure timezone awareness
                    if due_datetime and due_datetime.tzinfo is None:
                        due_datetime = due_datetime.replace(tzinfo=timezone.utc)
                    
                    agent.create_task(
                        tasklist_id=default_tasklist,
                        title=title,
                        due=due_datetime,
                        notes=notes
                    )
                    created_count += 1
                    print(f"✓ Tâche créée: {title}")
                except Exception as e:
                    skipped_count += 1
                    print(f"✗ Erreur lors de la création de {title}: {e}")
        
        # After processing, clear the extracted items file to avoid re‑processing
        try:
            with open("./json_files/extracted_items.json", "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.warning(f"Impossible de vider extracted_items.json: {e}")

        return {"created": created_count, "skipped": skipped_count}
    except Exception as e:
        st.error(f"Erreur lors de l'ajout des tâches: {e}")
        return {"created": 0, "skipped": 0}


def get_notes():
    """Récupère les notes"""
    return load_notes()

# -------------------------------------------------------
# DOWNLOAD TASKS TO LOCAL STORAGE
# -------------------------------------------------------
def download_tasks_to_local() -> int:
    """Fetch tasks from Google Tasks and merge them into ``extracted_items.json``.

    The function retrieves tasks from the first task list, converts each task to the
    internal ``extracted_items`` schema (category ``to_do``) and appends them to the
    existing ``extracted_items.json`` file. It returns the number of tasks added.
    """
    try:
        agent = EaseTasksAgent()
        tasklists = agent.list_tasklists()
        if not tasklists:
            st.warning("Aucune liste de tâches trouvée dans Google Tasks.")
            return 0
        # Use the first task list by default
        default_tasklist = tasklists[0]["id"]
        # Retrieve tasks without completed ones (show_completed=False) and filter just in case
        tasks = agent.get_tasks(default_tasklist, show_completed=False)
        # Ensure we only keep tasks that are not completed
        tasks = [t for t in tasks if t.get("status") != "completed"]
        if not tasks:
            st.info("Aucune tâche à télécharger.")
            return 0

        # Load existing extracted items (or start with an empty list)
        extracted_path = "./json_files/extracted_items.json"
        if os.path.exists(extracted_path):
            with open(extracted_path, "r", encoding="utf-8") as f:
                extracted_items = json.load(f)
        else:
            extracted_items = []

        # Transform Google Tasks entries into the expected schema
        new_items = []
        for task in tasks:
            # Basic mapping – title becomes the text, status is kept for reference
            new_items.append({
                "category": "to_do",
                "text": task.get("title", "Sans titre"),
                "status": task.get("status", "needsAction"),
                # Optional fields that downstream code may use
                "datetime_iso": None,
                "datetime_raw": None,
            })

        # Append and write back
        extracted_items.extend(new_items)
        with open(extracted_path, "w", encoding="utf-8") as f:
            json.dump(extracted_items, f, ensure_ascii=False, indent=2)
        return len(new_items)
    except Exception as e:
        st.error(f"Erreur lors du téléchargement des tâches : {e}")
        return 0







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

# Sidebar with Tasks and Notes
with st.sidebar:
    st.subheader("📝 Mes Tâches")
    
    if st.button("🔄 Actualiser les tâches", key="refresh_tasks"):
        st.rerun()

    # New button: download tasks from Google Tasks to local storage
    if st.button("📥 Télécharger les tâches locales", key="download_tasks"):
        count = download_tasks_to_local()
        if count:
            st.success(f"✅ {count} tâche(s) téléchargée(s) dans ./json_files/tasks.json.")
        else:
            st.info("Aucune tâche téléchargée.")
    
    try:
        tasks = get_google_tasks()
        
        if tasks:
            # Séparer les tâches complétées et en attente
            pending_tasks = [t for t in tasks if t["status"] == "needsAction"]
            completed_tasks = [t for t in tasks if t["status"] == "completed"]
            
            st.markdown(f"**Tâches en attente:** {len(pending_tasks)}")
            for task in pending_tasks[:10]:  # Afficher max 10
                # Use a unique key based on task ID; Streamlit automatically manages its state
                checkbox_key = f"task_{task['task_id']}"
                checked = st.checkbox(
                    f"{task['title']} ({task['list']})",
                    key=checkbox_key
                )
                # When the user checks the box, mark the task as completed in Google Tasks
                if checked and not st.session_state.get(f"completed_{task['task_id']}", False):
                    try:
                        agent = EaseTasksAgent()
                        agent.complete_task(task['list_id'], task['task_id'])
                        st.success(f"✅ Tâche '{task['title']}' marquée comme terminée.")
                        st.session_state[f"completed_{task['task_id']}"] = True
                    except Exception as e:
                        st.error(f"❌ Erreur lors du marquage de la tâche comme terminée : {e}")
            
            if completed_tasks:
                with st.expander(f"✅ Tâches complétées ({len(completed_tasks)})"):
                    for task in completed_tasks[:10]:
                        col_task, col_btn = st.columns([4, 1])
                        with col_task:
                            st.markdown(f"~~{task['title']}~~ ({task['list']})")
                        with col_btn:
                            undo_key = f"undo_{task['task_id']}"
                            if st.button("↩️", key=undo_key):
                                try:
                                    agent = EaseTasksAgent()
                                    agent.reopen_task(task['list_id'], task['task_id'])
                                    st.success(f"✅ Tâche '{task['title']}' réactivée.")
                                    # Refresh the sidebar to reflect the change
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erreur lors de la réactivation : {e}")
        else:
            st.info("Aucune tâche trouvée")
    except Exception as e:
        st.warning(f"Impossible de charger les tâches: {e}")
    
    st.divider()
    
    st.subheader("📝 Mes Notes")
    
    if st.button("🔄 Actualiser les notes", key="refresh_notes"):
        st.rerun()
    
    try:
        notes = get_notes()
        
        if notes:
            active_notes = [n for n in notes if not n.get("archived", False)]
            archived_notes = [n for n in notes if n.get("archived", False)]
            
            st.markdown(f"**Notes actives:** {len(active_notes)}")
            for note in active_notes[:10]:
                with st.expander(f"📄 {note['title'][:30]}"):
                    st.write(note['text'][:200])
                    if len(note['text']) > 200:
                        st.caption("... (texte coupé)")
        else:
            st.info("Aucune note trouvée")
    except Exception as e:
        st.warning(f"Impossible de charger les notes: {e}")

col_chat, col_calendar = st.columns([2, 1], gap="large")

# -------------------------------------------------------
# GOOGLE CALENDAR
# -------------------------------------------------------
with col_calendar:
    # Button to transfer Google Agenda data to local storage
    if st.button("📥 Transférer les données de l'agenda en local"):
        try:
            google_agenda_agent()
            st.success("✅ Les événements de l'agenda ont été synchronisés localement.")
        except Exception as e:
            st.error(f"❌ Erreur lors de la synchronisation de l'agenda : {e}")

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
        # Use a stable hash based only on the content to avoid duplicate processing
        message_id = hash(final_input)
        
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
    # SUGGESTIONS SECTION
    # -------------------------------------------------------
    # Initialise click counter if not present
    if "suggest_clicks" not in st.session_state:
        st.session_state.suggest_clicks = 0

    # Provide a button to generate suggestions (max 5 times per session)
    if st.session_state.suggest_clicks < 5:
        if st.button("💡 Afficher des suggestions"):
            st.session_state.suggest_clicks += 1
            # Run the smart suggestion agent; it will read the latest extracted items
            result = smart_suggest()
            # Display the JSON output directly
            st.subheader("Suggestions générées")
            st.json(result.get("output", {}))
    else:
        st.info("Vous avez atteint le nombre maximal de 5 suggestions pour cette session.")

    # -------------------------------------------------------
    # OPTIONS DE SAUVEGARDE (avant le traitement des messages)
    # -------------------------------------------------------
    if st.session_state.pending_save and st.session_state.last_extracted:
        st.write("---")
        st.write("Souhaites-tu enregistrer ces informations ?")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Oui, ajouter"):
                # Work on a copy to avoid accidental reuse of stale data
                current_items = st.session_state.last_extracted or []
                ajouter_items_si_user_accepte(current_items, True)
                st.success("Les éléments ont été ajoutés.")

                # Si des éléments "agenda" existent, créer les événements Google Calendar
                agenda_items = [item for item in current_items if item.get("category") == "agenda"]
                if agenda_items:
                    with st.spinner(" Ajout des événements au calendrier..."):
                        result = create_events_from_json()
                        st.success(f" {result['created']} événement(s) ajouté(s) au calendrier!")
                        if result['skipped'] > 0:
                            st.warning(f" {result['skipped']} événement(s) ignoré(s) (créneau pris ou erreur)")

                # Si des éléments "to_do" existent, créer les tâches Google Tasks
                todo_items = [item for item in current_items if item.get("category") == "to_do"]
                if todo_items:
                    with st.spinner(" Ajout des tâches..."):
                        result = add_tasks_to_google(current_items)
                        st.success(f" {result['created']} tâche(s) ajoutée(s) à Google Tasks!")
                        if result['skipped'] > 0:
                            st.warning(f" {result['skipped']} tâche(s) ignorée(s)")

                # Si des éléments "note" existent, créer les notes locales
                note_items = [item for item in current_items if item.get("category") == "note"]
                if note_items:
                    with st.spinner(" Ajout des notes..."):
                        result = add_notes_to_local(current_items)
                        st.success(f" {result['created']} note(s) ajoutée(s)!")
                        if result['skipped'] > 0:
                            st.warning(f" {result['skipped']} note(s) ignorée(s)")
                # Reset temporary variables
                current_items = []
                st.session_state.pending_save = False
                st.session_state.last_extracted = []
                st.session_state.last_message_id = None  # Clear to prevent re-processing

        with col2:
            if st.button("Non, annuler"):
                st.info("Aucun élément n'a été ajouté.")
                st.session_state.pending_save = False
                st.session_state.last_extracted = None
                st.session_state.last_message_id = None  # Clear to prevent re-processing