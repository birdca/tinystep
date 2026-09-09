"""Local persistence store for tinystep."""

import json
from pathlib import Path
from dataclasses import asdict
from datetime import datetime, date, timedelta
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
                "last_date": datetime.now().strftime("%Y-%m-%d"),
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

    def check_and_rollover_day(self, today_str: Optional[str] = None) -> Optional[str]:
        """檢查日期是否跨日。若跨日，自動將昨日進度存入 history，並重置今日任務狀態。"""
        if today_str is None:
            today_str = datetime.now().strftime("%Y-%m-%d")
        
        data = self.load()
        last_date = data.get("last_date")
        
        # 若無 last_date，但已有完成任務，表示為昨日遺留狀態
        if not last_date:
            has_completions = any(t.get("completed") for t in data.get("tasks", []))
            if has_completions:
                last_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            else:
                data["last_date"] = today_str
                self.save(data)
                return None
        
        if last_date != today_str:
            # 跨日歸檔
            completed_tasks = [t["id"] for t in data.get("tasks", []) if t.get("completed")]
            downscaled_tasks = [t["id"] for t in data.get("tasks", []) if t.get("is_downscaled")]
            
            if "history" not in data:
                data["history"] = {}
                
            data["history"][last_date] = {
                "completed": completed_tasks,
                "downscaled": downscaled_tasks,
                "completion_count": len(completed_tasks),
                "total_tasks": len(data.get("tasks", []))
            }
            
            # 重置今日狀態為全新待辦
            for t in data.get("tasks", []):
                t["completed"] = False
                t["is_downscaled"] = False
                t["completed_at"] = None
                
            data["last_date"] = today_str
            self.save(data)
            return last_date
            
        return None

    def calculate_streak(self) -> int:
        """計算連續打卡天數 (Current Streak)"""
        data = self.load()
        history = data.get("history", {})
        
        # 檢查今天是否有打卡
        today_has_completion = any(t.get("completed") for t in data.get("tasks", []))
        
        streak = 1 if today_has_completion else 0
        
        # 往前追溯歷史連續天數
        current_check_date = datetime.now().date() - timedelta(days=1)
        
        while True:
            date_key = current_check_date.strftime("%Y-%m-%d")
            record = history.get(date_key)
            if record and len(record.get("completed", [])) > 0:
                streak += 1
                current_check_date -= timedelta(days=1)
            else:
                break
                
        return streak

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
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for t in data["tasks"]:
            if t["id"] == task_id:
                t["completed"] = completed
                t["completed_at"] = now_str if completed else None
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
            t["completed_at"] = None
        data["last_date"] = datetime.now().strftime("%Y-%m-%d")
        self.save(data)

    def clear_all(self):
        """清空所有自訂的身分與任務，回到全新起始狀態"""
        data = self.load()
        data["identities"] = []
        data["tasks"] = []
        data["history"] = {}
        data["last_date"] = datetime.now().strftime("%Y-%m-%d")
        self.save(data)

    def load_from_dict(self, template_data: Dict[str, Any]):
        """載入範本資料"""
        data = self.load()
        if "identities" in template_data:
            data["identities"] = template_data["identities"]
        if "tasks" in template_data:
            data["tasks"] = template_data["tasks"]
        data["last_date"] = datetime.now().strftime("%Y-%m-%d")
        self.save(data)
