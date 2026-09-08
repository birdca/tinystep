"""Capacity & Overestimation Calculator based on Cognitive Science & Planning Fallacy."""

from typing import List
from .models import HabitTask, UserProfile, DailyPlan

class CapacityCalculator:
    def __init__(self, profile: UserProfile = None):
        self.profile = profile or UserProfile()

    def evaluate(self, tasks: List[HabitTask], available_hours: float, date_str: str) -> DailyPlan:
        """計算每日任務負荷並診斷是否過度預估 (Overestimation Check)"""
        active_tasks = [t for t in tasks]
        
        raw_minutes = 0
        buffered_minutes = 0.0
        
        for task in active_tasks:
            if task.is_downscaled:
                eff_min = 2
                raw_minutes += eff_min
                buffered_minutes += eff_min
            else:
                raw_minutes += task.estimated_minutes
                buffered_minutes += task.estimated_minutes * task.friction_weight * self.profile.planning_fallacy_multiplier

        num_tasks = len(active_tasks)
        context_penalty = num_tasks * self.profile.context_switch_minutes if num_tasks > 0 else 0
        total_effective_minutes = buffered_minutes + context_penalty
        
        sustainable_minutes = available_hours * 60 * self.profile.sustainable_capacity_ratio
        
        if sustainable_minutes > 0:
            load_ratio = total_effective_minutes / sustainable_minutes
        else:
            load_ratio = 9.99

        if load_ratio <= 0.75:
            status = "OPTIMAL"
        elif load_ratio <= 1.00:
            status = "STRETCH"
        else:
            status = "OVERLOAD"

        advice = self._generate_advice(status, load_ratio, active_tasks, available_hours)

        return DailyPlan(
            date_str=date_str,
            available_hours=available_hours,
            tasks=active_tasks,
            raw_minutes=raw_minutes,
            buffered_minutes=round(buffered_minutes, 1),
            context_switch_penalty_minutes=context_penalty,
            total_effective_minutes=round(total_effective_minutes, 1),
            load_ratio=round(load_ratio, 2),
            capacity_status=status,
            advice=advice
        )

    def _generate_advice(self, status: str, load_ratio: float, tasks: List[HabitTask], available_hours: float) -> List[str]:
        advice = []
        pct = int(load_ratio * 100)
        
        if status == "OVERLOAD":
            advice.append(f"⚠️ 【警報：嚴重超載】今日預估負荷達 {pct}%！已觸發規劃謬誤（Planning Fallacy）。")
            advice.append("💡 《原子習慣》核心策略：與其全盤放棄，不如採取『微步降級（2-Minute Rule）』或『主題日輪替』。")
            high_friction = [t for t in tasks if not t.is_downscaled and t.friction_weight >= 1.3]
            if high_friction:
                suggest_targets = ", ".join([f"【{t.id}】{t.title}" for t in high_friction[:2]])
                advice.append(f"👉 建議執行命令 `tinystep downscale <ID>` 降級高阻力任務：{suggest_targets}")
        elif status == "STRETCH":
            advice.append(f"⚡ 【注意：高強度負荷】今日負荷為 {pct}%，需耗費極大意志力。")
            advice.append("💡 建議確保任務間有充分間歇，並備妥環境提示（Make it obvious），避免在精力低谷時中斷。")
        else:
            advice.append(f"✅ 【節奏完美】今日負荷為 {pct}%，步調穩健且具備餘裕，最容易進入心流並維持長期習慣複利！")
            
        return advice
