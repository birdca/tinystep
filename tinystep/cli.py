"""Command-Line Interface for tinystep personal agent."""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.markup import escape
from rich import box

from .models import HabitTask, Identity
from .storage import Storage
from .capacity_calc import CapacityCalculator
from .habit_engine import HabitEngine
from .auto_builder import build_from_goal_text

console = Console()

def get_day_name() -> str:
    return datetime.now().strftime("%a")

def show_onboarding():
    panel_content = """[bold green]🌱 歡迎使用 TinyStep（原子習慣個人產能 Agent）！[/bold green]
目前系統處於全新乾淨狀態，尚未建立任何身分與任務。

[bold cyan]💡 你可以透過以下方式開始：[/bold cyan]
  1. [bold yellow]🤖 智慧引導初始化（最推薦）：[/bold yellow]
     直接輸入你想做的目標與任務清單，由 Agent 自動拆解出身分認同、阻力係數與兩分鐘降級版本：
     [white]tinystep init -i[/white]

  2. [bold yellow]➕ 隨時新增單一目標 (Agent 智慧解析)：[/bold yellow]
     [white]tinystep add "每天慢跑 30分鐘"[/white] 或直接輸入 [white]tinystep add[/white] 啟動互動精靈

  3. [bold yellow]📦 載入範本體驗 (運動/閱讀/反思)：[/bold yellow]
     [white]tinystep init --template general[/white]

隨時輸入 [bold cyan]tinystep --help[/bold cyan] 查看完整指令。
"""
    console.print(Panel(panel_content, title="🚀 [bold]新手起步指南 (Getting Started)[/bold]", border_style="cyan"))

def show_plan(args):
    storage = Storage()
    profile = storage.get_profile()
    tasks = storage.get_tasks()
    identities = {i.id: i for i in storage.get_identities()}
    today_name = get_day_name()
    today_str = datetime.now().strftime("%Y-%m-%d (%a)")
    streak = storage.calculate_streak()

    if not tasks:
        show_onboarding()
        return

    if args.hours is not None:
        hours = args.hours
    else:
        is_weekend = today_name in ["Sat", "Sun"]
        hours = profile.default_available_hours_weekend if is_weekend else profile.default_available_hours_weekday

    if getattr(args, "all", False):
        active_tasks = tasks
    else:
        active_tasks = [t for t in tasks if today_name in t.schedule_days or t.is_core_daily]

    calculator = CapacityCalculator(profile)
    plan = calculator.evaluate(active_tasks, hours, today_str)

    status_color = "green" if plan.capacity_status == "OPTIMAL" else ("yellow" if plan.capacity_status == "STRETCH" else "bold red")
    meter_bars = int(min(plan.load_ratio, 2.0) * 20)
    meter_str = "█" * meter_bars + "░" * max(0, 20 - meter_bars)

    summary_text = Text()
    summary_text.append(f"📅 日期：{today_str}  |  可支配專注時數：{hours} 小時  |  🔥 連續打卡：{streak} 天\n", style="bold")
    summary_text.append(f"📊 負荷指標：[{meter_str}] {int(plan.load_ratio * 100)}% ({plan.capacity_status})\n", style=status_color)
    summary_text.append(f"⏱️ 原始預估：{plan.raw_minutes} 分鐘  ➔  校正後總負荷（含阻力與 1.4x 緩衝）：{plan.buffered_minutes} 分鐘\n")
    summary_text.append(f"🔄 認知切換耗損：{plan.context_switch_penalty_minutes} 分鐘  ➔  等效專注總時數：{round(plan.total_effective_minutes / 60, 1)} 小時\n")
    summary_text.append(f"🛡️ 70% 可持續餘裕上限：{round(hours * 0.7, 1)} 小時 (保留 30% 彈性避免意志力崩潰)")

    console.print(Panel(summary_text, title="🌱 [bold cyan]TinyStep 個人成長與產能監控儀表板[/bold cyan]", border_style=status_color))

    if plan.advice:
        advice_panel = "\n".join(plan.advice)
        console.print(Panel(advice_panel, title="💡 [bold yellow]《原子習慣》調度建言[/bold yellow]", border_style="yellow"))

    table = Table(title=f"📋 今日任務與身分投票清單 (共 {len(active_tasks)} 項)", box=box.ROUNDED)
    table.add_column("狀態", justify="center", style="bold")
    table.add_column("ID", style="cyan")
    table.add_column("身分目標 / 任務名稱", style="white")
    table.add_column("預估時間", justify="right")
    table.add_column("微步降級版本 (2-Min Rule)", style="italic dim")

    for t in active_tasks:
        iden = identities.get(t.identity_id)
        iden_name = f"[{escape(iden.name)}] " if iden else ""
        
        status_icon = "✅ 完成" if t.completed else ("⚡ 微步中" if t.is_downscaled else "⏳ 待辦")
        time_str = "2 分鐘 (微步)" if t.is_downscaled else f"{t.estimated_minutes} 分鐘"
        
        row_style = "green" if t.completed else ("yellow" if t.is_downscaled else "white")
        table.add_row(
            status_icon,
            t.id,
            f"{iden_name}{t.title}",
            time_str,
            t.two_minute_rule,
            style=row_style
        )

    console.print(table)
    console.print("[dim]提示：輸入 [bold]tinystep check <ID>[/bold] 完成打卡並為身分投票；輸入 [bold]tinystep downscale <ID>[/bold] 啟動兩分鐘微步降級。[/dim]\n")

def downscale_task(args):
    storage = Storage()
    if storage.update_task_downscale(args.task_id, True):
        console.print(f"[bold yellow]⚡ 已成功將任務 【{escape(args.task_id)}】 降級為『兩分鐘微步版本 (2-Minute Rule)』！[/bold yellow]")
        console.print("[dim]在精力低下時，最重要的是保持習慣鏈條不斷裂，而非追求完美。[/dim]")
        show_plan(argparse.Namespace(hours=None, all=False))
    else:
        console.print(f"[bold red]❌ 找不到任務 ID: {escape(args.task_id)}[/bold red]")

def restore_task(args):
    storage = Storage()
    if storage.update_task_downscale(args.task_id, False):
        console.print(f"[bold green]🔄 已將任務 【{escape(args.task_id)}】 恢復為常規完整時間！[/bold green]")
        show_plan(argparse.Namespace(hours=None, all=False))
    else:
        console.print(f"[bold red]❌ 找不到任務 ID: {escape(args.task_id)}[/bold red]")

def check_task(args):
    storage = Storage()
    found, identity_id = storage.mark_task_complete(args.task_id, True)
    if found:
        identities = {i.id: i for i in storage.get_identities()}
        iden = identities.get(identity_id)
        console.print(f"[bold green]🎉 太棒了！已完成任務 【{escape(args.task_id)}】！[/bold green]")
        if iden:
            console.print(f"🗳️  為你的未來身分 [bold cyan]『{escape(iden.name)}』[/bold cyan] 成功投下一票！(目前累計: {iden.votes} 票)")
        console.print(f"[italic yellow]{HabitEngine.get_identity_quote()}[/italic yellow]\n")
    else:
        console.print(f"[bold red]❌ 找不到任務 ID: {escape(args.task_id)}[/bold red]")

def show_identities(args):
    storage = Storage()
    identities = storage.get_identities()
    streak = storage.calculate_streak()
    if not identities:
        console.print("[yellow]目前尚未建立任何身分認同。可使用 `tinystep add-identity` 或 `tinystep add` 新增！[/yellow]")
        return
    table = Table(title=f"🗳️ 身分認同票箱 (Identity Board)  |  🔥 連續打卡：{streak} 天", box=box.ROUNDED)
    table.add_column("身分代號", style="cyan")
    table.add_column("理想身分定義", style="bold white")
    table.add_column("認同宣言 (Identity Statement)", style="italic")
    table.add_column("累計票數", justify="right", style="bold green")

    for i in identities:
        table.add_row(i.id, i.name, i.statement, str(i.votes))
    console.print(table)

def show_history(args):
    storage = Storage()
    data = storage.load()
    history = data.get("history", {})
    streak = storage.calculate_streak()
    if not history:
        console.print("[yellow]目前尚無歷史封存紀錄。持續打卡到明天就會自動生成歷史報告！[/yellow]")
        return
    table = Table(title=f"📜 歷史每日打卡紀錄 (目前連續打卡：{streak} 天)", box=box.ROUNDED)
    table.add_column("日期", style="cyan")
    table.add_column("完成狀況", justify="center")
    table.add_column("完成項目清單", style="green")
    table.add_column("微步降級項目", style="yellow")
    for d, record in sorted(history.items(), reverse=True):
        completed = ", ".join(record.get("completed", [])) or "無"
        downscaled = ", ".join(record.get("downscaled", [])) or "無"
        total = record.get("total_tasks", 0)
        c_count = record.get("completion_count", 0)
        table.add_row(d, f"{c_count} / {total} 項完成", completed, downscaled)
    console.print(table)

def show_stack(args):
    storage = Storage()
    tasks = storage.get_tasks()
    if not tasks:
        console.print("[yellow]目前尚未建立任何習慣任務。可使用 `tinystep add` 新增！[/yellow]")
        return
    console.print(Panel(
        "《原子習慣》第一法則：讓提示顯而易見 (Make it Obvious)。\n將新習慣綁定在已有舊習慣後面，大腦最不需要消耗意志力！",
        title="🔗 [bold cyan]今日習慣堆疊鏈 (Habit Stacking Sequence)[/bold cyan]"
    ))
    for t in tasks:
        console.print(f"🔹 [bold cyan]【{escape(t.id)}】[/bold cyan]: 在【[bold yellow]{t.habit_stack_anchor}[/bold yellow]】之後 ➔ 立即【[bold green]{t.title}[/bold green]】")
        if t.target_url:
            console.print(f"   🌐 直達連結: {t.target_url}")
    console.print()

def audit_overestimation(args):
    storage = Storage()
    tasks = storage.get_tasks()
    profile = storage.get_profile()

    if not tasks:
        console.print("[yellow]目前系統中無任務可供分析。請先使用 `tinystep add` 新增任務或執行 `tinystep init -i` 智慧引導！[/yellow]")
        return

    all_raw_minutes = sum(t.estimated_minutes for t in tasks)
    buffered = sum(t.estimated_minutes * t.friction_weight * profile.planning_fallacy_multiplier for t in tasks)
    switches = len(tasks) * profile.context_switch_minutes
    total_effective = buffered + switches
    sustainable = profile.default_available_hours_weekday * 60 * profile.sustainable_capacity_ratio
    load_pct = int((total_effective / sustainable) * 100) if sustainable > 0 else 999

    task_list_str = "\n".join([f"  {idx+1}. 【{t.id}】{t.title} ({t.estimated_minutes}分鐘 / 阻力 {t.friction_weight})" for idx, t in enumerate(tasks)])

    report = f"""[bold red]🚨 當前任務清單之過度預估動態診斷[/bold red]

系統中目前共有 {len(tasks)} 項任務：
{task_list_str}

[bold underline]情境 A：直覺模式（假設全部塞在同一個工作日）[/bold underline]
  • 表面預估總時間：{all_raw_minutes} 分鐘 ({round(all_raw_minutes/60, 1)} 小時)
  • 加上規劃謬誤係數 (1.4x) 與阻力加權：{round(buffered, 1)} 分鐘
  • 跨領域情境切換損耗 ({len(tasks)} 次 x 15min)：+{switches} 分鐘
  • [bold red]真實等效專注總量：約 {round(total_effective/60, 1)} 小時！[/bold red]
  • 平日可支配時數 (3.5 小時 x 70% 永續上限)：僅 {round(sustainable/60, 1)} 小時
  • [bold {'red' if load_pct > 100 else 'green'}]超載指數：{load_pct}% ➔ {'【嚴重崩潰區】高機率半途而廢！' if load_pct > 100 else '【安全負荷】'}[/bold]

[bold underline]情境 B：TinyStep 智慧輪替解方（《原子習慣》系統思維）[/bold underline]
  • 設定 1 項每日不中斷核心習慣（如高頻小量任務）
  • 將高阻力主題拆分為『A/B 日輪替』或『週末集中實作』
  • 精力低落日善用 `tinystep downscale <ID>` 降為 2 分鐘版本，維持習慣鏈條不斷裂！
"""
    console.print(Panel(report, title="📊 [bold magenta]過度預估診斷報告 (Capacity Audit)[/bold magenta]", border_style="cyan"))

def add_task(args):
    """新增任務：支援自然語言輸入、Agent 智慧推導身分與原子習慣，亦相容手動參數"""
    storage = Storage()
    existing_identities = {i.id: i for i in storage.get_identities()}
    existing_tasks = {t.id: t for t in storage.get_tasks()}

    raw_goal = " ".join(args.goal).strip() if getattr(args, "goal", None) else None

    # 若未提供任何目標參數，且非指定 flags，啟動互動精靈
    if not raw_goal and not getattr(args, "id", None):
        console.print(Panel("""[bold green]🤖 TinyStep Agent 智慧目標新增精靈[/bold green]
你可以直接輸入你想新增的目標或每日任務，Agent 會自動為你：
  ✨ 提煉/關聯對應的[bold cyan]「理想身分認同 (Identity)」[/bold cyan]
  ⏱️ 自動解析預估專注時間與認知阻力
  🔗 自動生成[bold yellow]「習慣堆疊錨點」[/bold yellow]與[bold magenta]「兩分鐘微步 (2-Min Rule)」[/bold magenta]
""", title="➕ [bold]新增原子習慣[/bold]", border_style="cyan"))
        raw_goal = console.input("[bold yellow]請輸入你想新增的目標或任務（例如：每天慢跑 30分鐘、閱讀 20 頁）：[/bold yellow] ").strip()
        if not raw_goal:
            console.print("[yellow]未輸入任何內容，取消新增。[/yellow]")
            return

    new_identities, new_tasks = build_from_goal_text(raw_goal)
    if not new_tasks:
        console.print("[bold red]❌ 無法從輸入文字中解析出有效任務。[/bold red]")
        return

    for t in new_tasks:
        if args.minutes is not None:
            t.estimated_minutes = args.minutes
        if args.friction is not None:
            t.friction_weight = args.friction
        if args.identity:
            t.identity_id = args.identity
        if args.anchor:
            t.habit_stack_anchor = args.anchor
        if args.mvh:
            t.two_minute_rule = args.mvh
        if args.core:
            t.is_core_daily = True

        base_id = t.id
        counter = 1
        while t.id in existing_tasks:
            t.id = f"{base_id}_{counter}"
            counter += 1

    table = Table(title=f"✨ Agent 智慧推導新增清單 (共 {len(new_tasks)} 項任務)", box=box.ROUNDED)
    table.add_column("任務 ID", style="cyan")
    table.add_column("任務名稱", style="white")
    table.add_column("對應理想身分", style="bold green")
    table.add_column("時長/阻力", justify="right")
    table.add_column("習慣堆疊錨點", style="yellow")
    table.add_column("兩分鐘微步 (2-Min Rule)", style="italic magenta")

    for t in new_tasks:
        matched_iden = existing_identities.get(t.identity_id)
        if not matched_iden:
            for ni in new_identities:
                if ni.id == t.identity_id:
                    matched_iden = ni
                    break
        iden_name = matched_iden.name if matched_iden else "自律實踐者"
        table.add_row(
            t.id,
            t.title,
            iden_name,
            f"{t.estimated_minutes}m / {t.friction_weight}",
            t.habit_stack_anchor,
            t.two_minute_rule
        )

    console.print(table)

    added_count = 0
    for ni in new_identities:
        if ni.id not in existing_identities:
            storage.add_identity(ni)
            console.print(f"✨ 自動建立理想身分：[bold cyan]【{escape(ni.name)}】[/bold cyan] ({ni.statement})")

    for t in new_tasks:
        if storage.add_task(t):
            added_count += 1

    console.print(f"\n[bold green]🎉 成功加入 {added_count} 項原子習慣！正在即時重新計算今日產能負荷：[/bold green]\n")
    show_plan(argparse.Namespace(hours=None, all=False))

def remove_task(args):
    storage = Storage()
    if storage.delete_task(args.task_id):
        console.print(f"[bold green]🗑️  已成功刪除任務 【{escape(args.task_id)}】！[/bold green]")
    else:
        console.print(f"[bold red]❌ 找不到任務 ID: {escape(args.task_id)}[/bold red]")

def add_identity(args):
    storage = Storage()
    new_identity = Identity(
        id=args.id,
        name=args.name,
        statement=args.statement or f"我是一個持續精進 {args.name} 的人。"
    )
    if storage.add_identity(new_identity):
        console.print(f"[bold green]✅ 成功新增理想身分 【{escape(args.id)}】：{args.name}！[/bold green]")
    else:
        console.print(f"[bold red]❌ 身分 ID '{escape(args.id)}' 已經存在！[/bold red]")

def remove_identity(args):
    storage = Storage()
    if storage.delete_identity(args.identity_id):
        console.print(f"[bold green]🗑️  已成功刪除身分 【{escape(args.identity_id)}】！[/bold green]")
    else:
        console.print(f"[bold red]❌ 找不到身分 ID: {escape(args.identity_id)}[/bold red]")

def clear_all(args):
    storage = Storage()
    if not args.force:
        confirm = console.input("[bold red]⚠️ 警告：這將會清除所有任務、身分與歷史投票數據，恢復全新乾淨狀態！\n確認請輸入 'yes'：[/bold red] ")
        if confirm.strip().lower() != "yes":
            console.print("[yellow]已取消清除操作。[/yellow]")
            return
    storage.clear_all()
    console.print("[bold green]✨ 已成功清空所有個人化目標與身分！系統已恢復乾淨初始狀態。[/bold green]")
    console.print("[dim]隨時可透過 `tinystep init -i` 載入目標，或 `tinystep add` 建立新習慣。[/dim]")

def interactive_wizard(prefilled_text: str = None):
    """引導式對話精靈：接收目標清單並自動推導身分與原子習慣 (初始化全系統)"""
    console.print(Panel("""[bold green]🤖 歡迎使用 TinyStep 智慧習慣引導精靈！[/bold green]

你可以直接輸入一組目前的目標與想做的任務清單，Agent 會自動為你：
  ✨ 提煉出對應的[bold cyan]「理想身分認同 (Identity)」[/bold cyan]
  ⏱️ 自動解析預估專注時間與認知阻力權重
  🔗 自動生成[bold yellow]「習慣堆疊 (Habit Stacking)」[/bold yellow]錨點
  ⚡ 自動產出[bold magenta]「兩分鐘微步定律 (The 2-Minute Rule)」[/bold magenta]降級版本
  📊 評估今日負荷並診斷是否[bold red]「過度預估 (Overestimating)」[/bold red]！
""", title="🌱 [bold]目標與身分自動構建器[/bold]", border_style="cyan"))

    raw_text = prefilled_text
    if not raw_text:
        console.print("[bold yellow]請輸入你想養成的目標或每日任務清單（每行一項，輸入完成後連按兩次回車送出）：[/bold yellow]")
        lines = []
        try:
            while True:
                line = input()
                if not line.strip():
                    if lines:
                        break
                    else:
                        continue
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            pass
        raw_text = "\n".join(lines)

    if not raw_text.strip():
        console.print("[yellow]未輸入任何內容，取消構建。[/yellow]")
        return

    console.print("\n[dim]🧠 正在分析目標語意、提煉身分認同與習慣參數...[/dim]\n")
    identities, tasks = build_from_goal_text(raw_text)

    if not tasks:
        console.print("[red]❌ 無法從輸入文字中解析出有效任務。請重新嘗試！[/red]")
        return

    preview_table = Table(title=f"✨ 系統自動拆解成果預覽 (共提煉 {len(identities)} 個身分、{len(tasks)} 項原子任務)", box=box.ROUNDED)
    preview_table.add_column("任務代號", style="cyan")
    preview_table.add_column("任務名稱", style="white")
    preview_table.add_column("對應理想身分", style="bold green")
    preview_table.add_column("時長/阻力", justify="right")
    preview_table.add_column("習慣堆疊錨點", style="yellow")
    preview_table.add_column("兩分鐘微步 (2-Min Rule)", style="italic magenta")

    iden_lookup = {i.id: i for i in identities}
    for t in tasks:
        iden = iden_lookup.get(t.identity_id)
        iden_name = iden.name if iden else "自律實踐者"
        preview_table.add_row(
            t.id,
            t.title,
            iden_name,
            f"{t.estimated_minutes}m / {t.friction_weight}",
            t.habit_stack_anchor,
            t.two_minute_rule
        )
    console.print(preview_table)

    confirm = console.input("\n[bold cyan]是否確認將這組身分與任務建立至 TinyStep 系統？ [Y/n]: [/bold cyan]")
    if confirm.strip().lower() in ["", "y", "yes"]:
        storage = Storage()
        storage.clear_all()
        template_data = {
            "identities": [vars(i) for i in identities],
            "tasks": [vars(t) for t in tasks]
        }
        storage.load_from_dict(template_data)
        console.print("\n[bold green]🎉 成功建立！已為你生成專屬身分認同系統並初始化今日計畫：[/bold green]\n")
        show_plan(argparse.Namespace(hours=None, all=False))
    else:
        console.print("[yellow]已取消儲存。[/yellow]")

def load_template_by_name(template_name: str):
    storage = Storage()
    examples_dir = Path(__file__).resolve().parent.parent / "examples"
    available = [f.stem for f in examples_dir.glob("*.json")] if examples_dir.exists() else []
    template_file = examples_dir / f"{template_name}.json"
    if not template_file.exists():
        console.print(f"[bold red]❌ 找不到範本檔案: {template_name}[/bold red]")
        if available:
            console.print(f"目前可選範本：{', '.join(f'[cyan]{t}[/cyan]' for t in available)}")
        return
    with open(template_file, "r", encoding="utf-8") as f:
        template_data = json.load(f)
    storage.load_from_dict(template_data)
    console.print(f"[bold green]🎉 成功載入範本：{template_name}！[/bold green]")
    show_plan(argparse.Namespace(hours=None, all=False))

def init_system(args):
    storage = Storage()

    # 如果指定了 --text
    if getattr(args, "text", None):
        interactive_wizard(prefilled_text=args.text)
        return

    # 如果指定了 --interactive / -i
    if getattr(args, "interactive", False):
        interactive_wizard()
        return

    # 如果指定了 --template
    if getattr(args, "template", None):
        load_template_by_name(args.template)
        return

    # 如果指定了 --clean
    if getattr(args, "clean", False):
        storage.clear_all()
        console.print("[bold green]🌱 已初始化乾淨空白系統！[/bold green]")
        show_onboarding()
        return

    # 未指定任何參數時，提供互動式選單
    console.print(Panel("""[bold cyan]請選擇 TinyStep 初始化方式：[/bold cyan]
  [bold yellow][1][/bold yellow] 🤖 [bold]智慧引導模式[/bold]：直接輸入目標清單，由 Agent 自動拆解身分與原子習慣 (最推薦)
  [bold yellow][2][/bold yellow] 📦 [bold]載入內建範本[/bold]：套用現成的通用習慣範本 (general)
  [bold yellow][3][/bold yellow] 🧹 [bold]乾淨重置[/bold]：完全空白開局，手動自行配置
""", title="🌱 [bold]TinyStep 系統初始化[/bold]", border_style="cyan"))

    choice = console.input("[bold white]請輸入選項 [1/2/3] (預設 1): [/bold white]").strip()
    if choice in ["", "1"]:
        interactive_wizard()
    elif choice == "2":
        examples_dir = Path(__file__).resolve().parent.parent / "examples"
        available = [f.stem for f in examples_dir.glob("*.json")] if examples_dir.exists() else ["general"]
        console.print(f"可選範本：{', '.join(f'[cyan]{t}[/cyan]' for t in available)}")
        tmpl = console.input(f"請輸入範本名稱 (預設 general): ").strip() or "general"
        load_template_by_name(tmpl)
    elif choice == "3":
        storage.clear_all()
        console.print("[bold green]🌱 已初始化乾淨空白系統！[/bold green]")
        show_onboarding()
    else:
        console.print("[yellow]無效選項，已取消操作。[/yellow]")

def export_data(args):
    storage = Storage()
    data = storage.load()
    out_path = Path(args.filepath)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"[bold green]📦 成功將現有設定匯出至：{out_path}[/bold green]")

def import_data(args):
    storage = Storage()
    in_path = Path(args.filepath)
    if not in_path.exists():
        console.print(f"[bold red]❌ 找不到檔案: {in_path}[/bold red]")
        return
    with open(in_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    storage.load_from_dict(data)
    console.print(f"[bold green]📥 成功從 {in_path} 匯入資料！[/bold green]")
    show_plan(argparse.Namespace(hours=None, all=False))

def main():
    parser = argparse.ArgumentParser(
        prog="tinystep",
        description="TinyStep: 開源個人成長、產能調度與過度預估計算 Agent"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="子指令清單")

    # init
    init_p = subparsers.add_parser("init", help="初始化系統 (智慧引導、套用範本或空白開局)")
    init_p.add_argument("--interactive", "-i", action="store_true", help="啟動對話式智慧引導精靈，直接輸入目標由系統自動拆解")
    init_p.add_argument("--text", type=str, default=None, help="直接以文字傳入目標清單 (例如 '每天刷題 30m; 研讀系統設計 45m')")
    init_p.add_argument("--template", "-t", type=str, help="套用內建範本名稱 (例如 general)")
    init_p.add_argument("--clean", action="store_true", help="初始化為全新空白系統")

    # plan
    plan_parser = subparsers.add_parser("plan", help="檢視今日計畫、負荷指標與過度預估診斷")
    plan_parser.add_argument("--hours", type=float, default=None, help="自訂今日可支配專注時數 (預設平日 3.5h, 週末 5h)")
    plan_parser.add_argument("--all", action="store_true", help="強制顯示所有任務（不論輪替排程）")

    # check
    check_parser = subparsers.add_parser("check", help="完成打卡並為理想身分投下一票")
    check_parser.add_argument("task_id", type=str, help="任務代號")

    # downscale
    downscale_parser = subparsers.add_parser("downscale", help="啟動兩分鐘定律微步降級 (降低阻力、保護連續打卡)")
    downscale_parser.add_argument("task_id", type=str, help="任務代號")

    # restore
    restore_parser = subparsers.add_parser("restore", help="恢復為完整常規任務時間")
    restore_parser.add_argument("task_id", type=str, help="任務代號")

    # stack
    subparsers.add_parser("stack", help="檢視習慣堆疊錨點與執行意圖")

    # identities
    subparsers.add_parser("identities", help="檢視身分認同得票箱")

    # history
    subparsers.add_parser("history", help="檢視歷史每日打卡紀錄與連續天數")

    # add-identity
    add_iden_p = subparsers.add_parser("add-identity", help="新增理想身分認同")
    add_iden_p.add_argument("id", type=str, help="身分代號 (例如 writer, athlete)")
    add_iden_p.add_argument("name", type=str, help="身分名稱 (例如 作家, 運動員)")
    add_iden_p.add_argument("--statement", type=str, default="", help="認同宣言")

    # remove-identity
    rm_iden_p = subparsers.add_parser("remove-identity", help="刪除指定身分")
    rm_iden_p.add_argument("identity_id", type=str, help="身分代號")

    # audit
    subparsers.add_parser("audit", help="動態過度預估審查報告 (評估當前所有任務之總負荷)")

    # add (支援自然語言、Agent 智慧推導身分與任務，亦支援手動參數)
    add_parser = subparsers.add_parser("add", help="新增原子習慣 (支援 Agent 自然語言解析與身分自動建立)")
    add_parser.add_argument("goal", nargs="*", help="自然語言目標或任務描述 (例如 '每天慢跑 30分鐘')，留空則啟動互動精靈")
    add_parser.add_argument("--interactive", "-i", action="store_true", help="啟動對話式精靈新增")
    add_parser.add_argument("--minutes", type=int, default=None, help="手動指定預估時間 (分鐘)")
    add_parser.add_argument("--friction", type=float, default=None, help="手動指定阻力係數 (1.0~1.5)")
    add_parser.add_argument("--identity", type=str, default=None, help="手動指定身分代號")
    add_parser.add_argument("--anchor", type=str, default=None, help="手動指定習慣堆疊錨點")
    add_parser.add_argument("--mvh", type=str, default=None, help="手動指定兩分鐘微步版本")
    add_parser.add_argument("--core", action="store_true", help="是否為每日必做核心習慣")

    # remove
    rm_parser = subparsers.add_parser("remove", help="刪除指定任務")
    rm_parser.add_argument("task_id", type=str, help="任務代號")

    # clear
    clear_p = subparsers.add_parser("clear", help="清除所有個人化目標與身分 (全新開局)")
    clear_p.add_argument("--force", "-f", action="store_true", help="強制清除無需輸入確認")

    # reset
    subparsers.add_parser("reset", help="重置今日任務打卡狀態")

    # export
    exp_p = subparsers.add_parser("export", help="匯出當前習慣與身分設定至 JSON 檔案")
    exp_p.add_argument("filepath", type=str, help="輸出檔案路徑")

    # import
    imp_p = subparsers.add_parser("import", help="從 JSON 檔案匯入習慣與身分設定")
    imp_p.add_argument("filepath", type=str, help="匯入檔案路徑")

    # 全域跨日檢查：每次執行任何指令時，自動比對日期並自動歸檔昨日紀錄、重置今日任務
    storage = Storage()
    rolled_date = storage.check_and_rollover_day()
    if rolled_date:
        console.print(f"[bold cyan]🌅 新的一天已開啟（今日：{datetime.now().strftime('%Y-%m-%d')}）！[/bold cyan]")
        console.print(f"[dim]昨日 ({rolled_date}) 打卡紀錄已自動封存至歷史。今日任務已重置為全新待辦，開始為身分投票吧！[/dim]\n")

    if len(sys.argv) == 1:
        args = parser.parse_args(["plan"])
        show_plan(args)
        return

    args = parser.parse_args()

    if args.subcommand == "plan":
        show_plan(args)
    elif args.subcommand == "check":
        check_task(args)
    elif args.subcommand == "downscale":
        downscale_task(args)
    elif args.subcommand == "restore":
        restore_task(args)
    elif args.subcommand == "identities":
        show_identities(args)
    elif args.subcommand == "history":
        show_history(args)
    elif args.subcommand == "add-identity":
        add_identity(args)
    elif args.subcommand == "remove-identity":
        remove_identity(args)
    elif args.subcommand == "stack":
        show_stack(args)
    elif args.subcommand == "audit":
        audit_overestimation(args)
    elif args.subcommand == "add":
        add_task(args)
    elif args.subcommand == "remove":
        remove_task(args)
    elif args.subcommand == "clear":
        clear_all(args)
    elif args.subcommand == "init":
        init_system(args)
    elif args.subcommand == "export":
        export_data(args)
    elif args.subcommand == "import":
        import_data(args)
    elif args.subcommand == "reset":
        Storage().reset_daily_progress()
        console.print("[bold green]🔄 今日打卡進度已手動重置。[/bold green]")
        show_plan(argparse.Namespace(hours=None, all=False))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
