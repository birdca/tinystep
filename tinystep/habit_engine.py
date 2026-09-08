"""Atomic Habits behavioral engine: Identity voting, Habit Stacking & Two-Minute Rule."""

from typing import List
from .models import HabitTask, Identity

# 預設乾淨無任務（適合開源社群及隨時重置）
DEFAULT_IDENTITIES: List[Identity] = []
DEFAULT_TASKS: List[HabitTask] = []

class HabitEngine:
    @staticmethod
    def get_habit_stack_prompt(task: HabitTask) -> str:
        """根據第一法則（讓提示顯而易見），產生執行意圖與習慣堆疊語句"""
        anchor = task.habit_stack_anchor or "完成前一項動作"
        return f"👉 【習慣堆疊】在「{anchor}」之後，我會立即「{task.title}」。"

    @staticmethod
    def get_identity_quote() -> str:
        return "✨ 《原子習慣》提醒：你所採取的每一個行動，都是為你想成為的那種人投下一票！"
