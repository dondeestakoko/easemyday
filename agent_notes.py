"""
Google Keep Integration - Local JSON Mode
Notes are stored locally in JSON and can be synced to Google Keep later
"""
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NOTES_JSON_FILE = "./notes_data.json"


class EaseNotesAgent:
    """Gère les notes (mode JSON local)"""
    
    def __init__(self):
        """Initialise l'agent de notes"""
        self.notes_file = NOTES_JSON_FILE
        self.load_or_create_notes_file()
        print("[✓] Agent notes initialisé (JSON local)")
    
    def load_or_create_notes_file(self):
        """Charge ou crée le fichier de notes"""
        if not os.path.exists(self.notes_file):
            with open(self.notes_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _load_notes(self):
        """Charge les notes du fichier JSON"""
        try:
            with open(self.notes_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lors de la lecture des notes: {e}")
            return []
    
    def _save_notes(self, notes):
        """Sauvegarde les notes dans le fichier JSON"""
        try:
            with open(self.notes_file, "w", encoding="utf-8") as f:
                json.dump(notes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des notes: {e}")
    
    def authenticate(self):
        """Placeholder pour compatibilité"""
        pass
    
    def create_note(self, title: str, text: str, color: str = None):
        """
        Crée une nouvelle note
        
        Args:
            title: Titre de la note
            text: Contenu de la note
            color: Couleur optionnelle (RED, ORANGE, YELLOW, GREEN, TEAL, BLUE, PURPLE, BROWN, GRAY)
        
        Returns:
            dict: Informations sur la note créée
        """
        try:
            notes = self._load_notes()
            
            note_id = str(uuid.uuid4())
            note = {
                "id": note_id,
                "title": title,
                "text": text,
                "color": color if color in ["RED", "ORANGE", "YELLOW", "GREEN", "TEAL", "BLUE", "PURPLE", "BROWN", "GRAY"] else "YELLOW",
                "archived": False,
                "pinned": False,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            notes.append(note)
            self._save_notes(notes)
            
            print(f"[✓] Note créée: {title}")
            return {
                "success": True,
                "id": note_id,
                "title": note["title"],
                "text": note["text"],
                "created_at": note["created_at"]
            }
        except Exception as e:
            print(f"[✗] Erreur lors de la création de la note: {e}")
            return {"success": False, "error": str(e)}
    
    def get_all_notes(self):
        """
        Récupère toutes les notes
        
        Returns:
            list: Liste des notes avec titre et contenu
        """
        try:
            notes = self._load_notes()
            
            result = []
            for note in notes:
                result.append({
                    "id": note.get("id"),
                    "title": note.get("title", "Sans titre"),
                    "text": note.get("text", ""),
                    "color": note.get("color", "GRAY"),
                    "archived": note.get("archived", False),
                    "pinned": note.get("pinned", False)
                })
            
            return result
        except Exception as e:
            print(f"[✗] Erreur lors de la récupération des notes: {e}")
            return []
    
    def get_notes_by_title(self, title_filter: str = None):
        """
        Récupère les notes filtrées par titre (recherche partiellement)
        
        Args:
            title_filter: Chaîne à rechercher dans les titres
        
        Returns:
            list: Notes correspondantes
        """
        try:
            all_notes = self.get_all_notes()
            
            if title_filter:
                return [n for n in all_notes if title_filter.lower() in n["title"].lower()]
            
            return all_notes
        except Exception as e:
            print(f"[✗] Erreur lors du filtrage des notes: {e}")
            return []
    
    def update_note(self, note_id: str, title: str = None, text: str = None):
        """
        Met à jour une note existante
        
        Args:
            note_id: ID de la note à modifier
            title: Nouveau titre (optionnel)
            text: Nouveau contenu (optionnel)
        
        Returns:
            dict: Informations sur la note mise à jour
        """
        try:
            notes = self._load_notes()
            
            note = next((n for n in notes if n["id"] == note_id), None)
            if not note:
                return {"success": False, "error": "Note non trouvée"}
            
            if title:
                note["title"] = title
            if text:
                note["text"] = text
            
            note["updated_at"] = datetime.now().isoformat()
            self._save_notes(notes)
            
            return {
                "success": True,
                "id": note["id"],
                "title": note["title"],
                "text": note["text"],
                "updated_at": note["updated_at"]
            }
        except Exception as e:
            print(f"[✗] Erreur lors de la mise à jour de la note: {e}")
            return {"success": False, "error": str(e)}
    
    def delete_note(self, note_id: str):
        """
        Supprime une note
        
        Args:
            note_id: ID de la note à supprimer
        
        Returns:
            dict: Résultat de la suppression
        """
        try:
            notes = self._load_notes()
            
            note = next((n for n in notes if n["id"] == note_id), None)
            if not note:
                return {"success": False, "error": "Note non trouvée"}
            
            notes = [n for n in notes if n["id"] != note_id]
            self._save_notes(notes)
            
            return {
                "success": True,
                "deleted_id": note_id,
                "deleted_at": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"[✗] Erreur lors de la suppression de la note: {e}")
            return {"success": False, "error": str(e)}
    
    def archive_note(self, note_id: str):
        """
        Archive une note
        
        Args:
            note_id: ID de la note à archiver
        
        Returns:
            dict: Résultat de l'archivage
        """
        try:
            notes = self._load_notes()
            
            note = next((n for n in notes if n["id"] == note_id), None)
            if not note:
                return {"success": False, "error": "Note non trouvée"}
            
            note["archived"] = True
            note["updated_at"] = datetime.now().isoformat()
            self._save_notes(notes)
            
            return {
                "success": True,
                "id": note_id,
                "archived": True
            }
        except Exception as e:
            print(f"[✗] Erreur lors de l'archivage de la note: {e}")
            return {"success": False, "error": str(e)}
