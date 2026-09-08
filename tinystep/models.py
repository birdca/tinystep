"""Data models for tinystep - Atomic Habits & Capacity Management."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

@dataclass
class Identity:
    id: str
    name: str             # 例如："分散式系統架構師"
    statement: str        # 例如："我是一個能夠設計高可用、高併發架構的資深工程師"
    votes: int = 0        # 身分認同累積得票數

@dataclass
class HabitTask:
    id: str
    title: str
    identity_id: str
    estimated_minutes: int
    friction_weight: float     # 1.0 (瑣事) ~ 1.5 (高認知深度學習)
    habit_stack_anchor: str    # "在【早晨第一杯咖啡】之後"
    two_minute_rule: str       # 兩分鐘啟動降級版本
    target_url: Optional[str] = None
    schedule_days: List[str] = field(default_factory=lambda: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    is_core_daily: bool = False  # 是否為不可中斷的每日必做核心（如 LeetCode）
    is_downscaled: bool = False
    completed: bool = False
    completed_at: Optional[str] = None

@dataclass
class DailyPlan:
    date_str: str
    available_hours: float
    tasks: List[HabitTask] = field(default_factory=list)
    raw_minutes: int = 0
    buffered_minutes: float = 0.0
    context_switch_penalty_minutes: int = 0
    total_effective_minutes: float = 0.0
    load_ratio: float = 0.0
    capacity_status: str = "OPTIMAL"  # OPTIMAL (<75%), STRETCH (75-95%), OVERLOAD (>95%)
    advice: List[str] = field(default_factory=list)

@dataclass
class UserProfile:
    default_available_hours_weekday: float = 3.5
    default_available_hours_weekend: float = 5.0
    planning_fallacy_multiplier: float = 1.4
    context_switch_minutes: int = 15
    sustainable_capacity_ratio: float = 0.70  # 70% 規則，保留 30% 彈性緩衝
