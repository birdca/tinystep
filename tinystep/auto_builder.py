"""Automated goal deconstruction and Atomic Habits generator."""

import re
import hashlib
from typing import List, Tuple, Dict, Any
from .models import Identity, HabitTask

# 領域關鍵字與身分認同原型資料庫（依特異性排序）
DOMAIN_ARCHETYPES = [
    {
        "keywords": ["gcp", "aws", "azure", "雲端", "cloud", "docker", "k8s", "kubernetes", "證照", "ace"],
        "id": "cloud_engineer",
        "name": "雲端架構實戰工程師 (Cloud Solutions Engineer)",
        "statement": "我是一個精通現代雲端基礎設施、容器化與自動化維運架構的工程師。",
        "friction": 1.3,
        "default_minutes": 45,
        "anchor": "午休甦醒後洗把臉並坐在電腦前",
        "mvh": "閱讀 2 題雲端情境解析或瀏覽一次指令速查表 (2分鐘)"
    },
    {
        "keywords": ["leetcode", "刷題", "演算法", "code", "coding", "程式", "解題", "dsa", "力扣"],
        "id": "algorithm_coder",
        "name": "演算法直覺解題者 (Algorithmic Problem Solver)",
        "statement": "我是一個具備敏銳資料結構直覺、能寫出穩健優雅演算法的工程師。",
        "friction": 1.3,
        "default_minutes": 35,
        "anchor": "早晨刷牙洗漱並喝下第一杯水後",
        "mvh": "打開今日題目，讀完題目敘述並在筆記本寫下解題方向/虛擬碼 (2分鐘)"
    },
    {
        "keywords": ["ai", "agent", "llm", "機器學習", "深度學習", "模型", "deeplearning", "prompt"],
        "id": "ai_builder",
        "name": "AI Agent 系統建構者 (Agentic AI Builder)",
        "statement": "我是一個掌握自主代理人工作流與大語言模型工具鏈整合的核心實踐者。",
        "friction": 1.4,
        "default_minutes": 45,
        "anchor": "打開筆電開始專注工作前的第一件事",
        "mvh": "登入課程觀看 1 個單元的 2 分鐘簡介或運行 1 個 code cell (2分鐘)"
    },
    {
        "keywords": ["系統設計", "系統架構", "system design", "架構師", "微服務", "分散式", "高併發", "hellointerview", "架構"],
        "id": "sys_architect",
        "name": "分散式系統架構師 (Systems Architect)",
        "statement": "我是一個能夠深入洞察高併發、容錯與可擴展分散式系統架構的資深工程師。",
        "friction": 1.4,
        "default_minutes": 45,
        "anchor": "晚餐結束收拾完桌面並打開檯燈後",
        "mvh": "打開教材閱讀架構案例的 High-Level Architecture 結構圖 (2分鐘)"
    },
    {
        "keywords": ["運動", "慢跑", "跑步", "健身", "重訓", "散步", "瑜珈", "游泳", "workout", "run", "深蹲"],
        "id": "athlete",
        "name": "自律活力運動員 (Disciplined Athlete)",
        "statement": "我是一個重視身體能量管理、每天堅持活動筋骨的自律自強者。",
        "friction": 1.2,
        "default_minutes": 30,
        "anchor": "更換好運動服並穿上跑鞋時",
        "mvh": "繫好鞋帶走到戶外或鋪開瑜珈墊活動 2 分鐘"
    },
    {
        "keywords": ["閱讀", "看書", "讀書", "read", "書", "小說", "好書"],
        "id": "reader",
        "name": "終身深度閱讀者 (Lifelong Deep Reader)",
        "statement": "我是一個每日沉浸於好書、持續汲取前人智慧的終身學習者。",
        "friction": 1.1,
        "default_minutes": 30,
        "anchor": "睡前將手機放在書桌充電並坐上床沿時",
        "mvh": "翻開床頭書讀完第 1 頁 (2分鐘)"
    },
    {
        "keywords": ["寫作", "寫文章", "日記", "反思", "覆盤", "筆記", "write", "journal", "部落格"],
        "id": "writer",
        "name": "思維洞察記錄者 (Clarity Writer)",
        "statement": "我是一個透過書寫釐清思維、每天記錄個人成長與思考的觀察家。",
        "friction": 1.1,
        "default_minutes": 20,
        "anchor": "晚上刷牙洗臉後回到書桌前",
        "mvh": "打開筆記本寫下今日 1 件反思或感恩的事 (2分鐘)"
    },
    {
        "keywords": ["英文", "英語", "單字", "多益", "托福", "雅思", "podcast", "english"],
        "id": "language_learner",
        "name": "全球溝通學習者 (Global Communicator)",
        "statement": "我是一個每天沉浸於外語語境、自信連通全球思想的終身學習者。",
        "friction": 1.2,
        "default_minutes": 25,
        "anchor": "通勤戴上耳機或早晨泡咖啡時",
        "mvh": "打開外語音訊聽完 1 則 2 分鐘新聞或背 3 個單字 (2分鐘)"
    }
]

def extract_minutes(text: str, default: int = 30) -> int:
    hr_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:小時|hr|hrs|h)', text, re.IGNORECASE)
    if hr_match:
        return int(float(hr_match.group(1)) * 60)

    min_match = re.search(r'(\d+)\s*(?:分鐘|min|mins|m)', text, re.IGNORECASE)
    if min_match:
        return int(min_match.group(1))

    return default

def clean_title(text: str) -> str:
    cleaned = re.sub(r'^\s*(?:\d+[\.\、\)\-]|[\-\*•])\s*', '', text)
    cleaned = re.sub(r'\s*(\d+(?:\.\d+)?\s*(?:小時|hr|hrs|h|分鐘|min|mins|m))\s*$', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

def build_from_goal_text(raw_input: str) -> Tuple[List[Identity], List[HabitTask]]:
    lines = [l.strip() for l in re.split(r'[\r\n；;]+', raw_input) if l.strip()]
    
    identities_map: Dict[str, Identity] = {}
    tasks: List[HabitTask] = []

    for idx, line in enumerate(lines):
        clean = clean_title(line)
        if not clean:
            continue

        lower_line = line.lower()
        matched_archetype = None
        for arch in DOMAIN_ARCHETYPES:
            if any(k in lower_line for k in arch["keywords"]):
                matched_archetype = arch
                break

        minutes = extract_minutes(line, default=matched_archetype["default_minutes"] if matched_archetype else 30)

        if matched_archetype:
            iden_id = matched_archetype["id"]
            if iden_id not in identities_map:
                identities_map[iden_id] = Identity(
                    id=iden_id,
                    name=matched_archetype["name"],
                    statement=matched_archetype["statement"],
                    votes=0
                )
            task_id = f"{iden_id}_{idx+1}" if any(t.id == iden_id for t in tasks) else iden_id
            tasks.append(HabitTask(
                id=task_id,
                title=clean,
                identity_id=iden_id,
                estimated_minutes=minutes,
                friction_weight=matched_archetype["friction"],
                habit_stack_anchor=matched_archetype["anchor"],
                two_minute_rule=matched_archetype["mvh"],
                schedule_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                is_core_daily=False
            ))
        else:
            safe_slug = re.sub(r'[^a-zA-Z0-9]', '', hashlib.md5(clean.encode()).hexdigest()[:6])
            iden_id = f"identity_{safe_slug}"
            iden_name = f"{clean[:10]}實踐者"
            
            if iden_id not in identities_map:
                identities_map[iden_id] = Identity(
                    id=iden_id,
                    name=iden_name,
                    statement=f"我是一個持之以恆實踐【{clean}】並追求精進的人。",
                    votes=0
                )
            tasks.append(HabitTask(
                id=f"task_{safe_slug}",
                title=clean,
                identity_id=iden_id,
                estimated_minutes=minutes,
                friction_weight=1.2,
                habit_stack_anchor="完成一項日常例行公事之後",
                two_minute_rule=f"打開與【{clean[:10]}】相關的工具或筆記本，啟動 2 分鐘",
                schedule_days=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
                is_core_daily=False
            ))

    return list(identities_map.values()), tasks
