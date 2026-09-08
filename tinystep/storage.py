"""Local persistence store for tinystep."""

import json
from pathlib import Path
from dataclasses import asdict
from typing import Dict, Any, List, Optional
from .models import Identity, HabitTask, UserProfile

STORAGE_DIR = Path.home() / ".tinystep"
DATA_FILE = STORAGE_DIR / "data.json"

class Storage:
    def __init__(self, data_path: Path = DATA_FILE):
        self.data_path = data_path
        self._ensure_storage()

    def _ensure_storage(self):
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.data_path.exists():
            default_data = {
                "profile": asdict(UserProfile()),
                "identities": [],
                "tasks": [],
                "history": {}
            }
            self.save(default_data)

    def load(self) -> Dict[str, Any]:
        with open(self.data_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save(self, data: Dict[str, Any]):
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_identities(self) -> List[Identity]:
        data = self.load()
        return [Identity(**item) for item in data.get("identities", [])]

    def get_tasks(self) -> List[HabitTask]:
        data = self.load()
        return [HabitTask(**item) for item in data.get("tasks", [])]

    def get_profile(self) -> UserProfile:
        data = self.load()
        return UserProfile(**data.get("profile", {}))

    def add_identity(self, identity: Identity) -> bool:
        data = self.load()
        for i in data["identities"]:
            if i["id"] == identity.id:
                return False
        data["identities"].append(asdict(identity))
        self.save(data)
        return True

    def delete_identity(self, identity_id: str) -> bool:
        data = self.load()
        orig_len = len(data.get("identities", []))
        data["identities"] = [i for i in data.get("identities", []) if i["id"] != identity_id]
        if len(data["identities"]) < orig_len:
            self.save(data)
            return True
        return False

    def add_task(self, task: HabitTask) -> bool:
        data = self.load()
        for t in data["tasks"]:
            if t["id"] == task.id:
                return False
        data["tasks"].append(asdict(task))
        self.save(data)
        return True

    def delete_task(self, task_id: str) -> bool:
        data = self.load()
        orig_len = len(data.get("tasks", []))
        data["tasks"] = [t for t in data.get("tasks", []) if t["id"] != task_id]
        if len(data["tasks"]) < orig_len:
            self.save(data)
            return True
        return False

    def update_task_downscale(self, task_id: str, is_downscaled: bool) -> bool:
        data = self.load()
        found = False
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["is_downscaled"] = is_downscaled
                found = True
                break
        if found:
            self.save(data)
        return found

    def mark_task_complete(self, task_id: str, completed: bool = True) -> tuple[bool, str]:
        data = self.load()
        found = False
        identity_id = ""
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["completed"] = completed
                identity_id = t["identity_id"]
                found = True
                break
        if found:
            for i in data["identities"]:
                if i["id"] == identity_id:
                    if completed:
                        i["votes"] = i.get("votes", 0) + 1
                    break
            self.save(data)
        return found, identity_id

    def reset_daily_progress(self):
        data = self.load()
        for t in data["tasks"]:
            t["completed"] = False
            t["is_downscaled"] = False
        self.save(data)

    def clear_all(self):
        """清空所有自訂的身分與任務，回到全新起始狀態"""
        data = self.load()
        data["identities"] = []
        data["tasks"] = []
        data["history"] = {}
        self.save(data)

    def load_from_dict(self, template_data: Dict[str, Any]):
        """載入範本資料"""
        data = self.load()
        if "identities" in template_data:
            data["identities"] = template_data["identities"]
        if "tasks" in template_data:
            data["tasks"] = template_data["tasks"]
        self.save(data)
