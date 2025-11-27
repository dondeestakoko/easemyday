from typing import List, Dict, Optional
from datetime import datetime, timedelta
from get_tasks_service import get_tasks_service 


class EaseTasksAgent:
    def __init__(self):
        self.service = get_tasks_service()

    # 1. Lister les listes de tâches
    def list_tasklists(self) -> List[Dict]:
        results = self.service.tasklists().list().execute()
        return results.get("items", [])

    # 2. Lire les tâches d'une liste
    def get_tasks(self, tasklist_id: str, show_completed: bool = True) -> List[Dict]:
        results = self.service.tasks().list(
            tasklist=tasklist_id,
            showCompleted=show_completed
        ).execute()
        return results.get("items", [])

    # 3. Créer une tâche
    def create_task(
        self,
        tasklist_id: str,
        title: str,
        due: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Dict:
        body = {
            "title": title,
        }
        if due:
            # format RFC3339, ex: "2025-11-25T18:00:00.000Z"
            body["due"] = due.isoformat() + "Z"
        if notes:
            body["notes"] = notes

        task = self.service.tasks().insert(
            tasklist=tasklist_id, body=body
        ).execute()
        return task

    # 4. Marquer comme terminée
    def complete_task(self, tasklist_id: str, task_id: str) -> Dict:
        task = self.service.tasks().get(
            tasklist=tasklist_id,
            task=task_id
        ).execute()
        task["status"] = "completed"
        updated = self.service.tasks().update(
            tasklist=tasklist_id,
            task=task_id,
            body=task
        ).execute()
        return updated

    def reopen_task(self, tasklist_id: str, task_id: str) -> Dict:
        """Revert a completed task back to pending (needsAction).

        Google Tasks uses the ``status`` field where ``"needsAction"`` indicates a pending task.
        This method fetches the task, sets its status back to ``needsAction`` and updates it.
        """
        task = self.service.tasks().get(
            tasklist=tasklist_id,
            task=task_id
        ).execute()
        # Only change if it was completed to avoid unnecessary API calls
        if task.get("status") == "completed":
            task["status"] = "needsAction"
            updated = self.service.tasks().update(
                tasklist=tasklist_id,
                task=task_id,
                body=task
            ).execute()
            return updated
        # If already pending, just return the original task dict
        return task

    # 5. Modifier date d'échéance ou titre
    def update_task(
        self,
        tasklist_id: str,
        task_id: str,
        title: Optional[str] = None,
        due: Optional[datetime] = None,
        notes: Optional[str] = None
    ) -> Dict:
        task = self.service.tasks().get(
            tasklist=tasklist_id,
            task=task_id
        ).execute()

        if title:
            task["title"] = title
        if due:
            task["due"] = due.isoformat() + "Z"
        if notes:
            task["notes"] = notes

        updated = self.service.tasks().update(
            tasklist=tasklist_id,
            task=task_id,
            body=task
        ).execute()
        return updated

if __name__ == "__main__":
    agent = EaseTasksAgent()
    lists = agent.list_tasklists()
    print("Task Lists:")
    for lst in lists:
        print(f"- {lst['title']} (ID: {lst['id']})")