// 訊息視覺化與 Telegram 行內按鈕 (Inline Keyboard) 格式化

import { getTodayStr, getDayName, calculateStreak, calculateCapacity } from "./logic.js";

export function renderPlanMessage(data) {
  const todayStr = getTodayStr();
  const dayName = getDayName();
  const streak = calculateStreak(data);
  const cap = calculateCapacity(data);
  const tasks = cap.activeTasks;

  const meterBars = Math.min(20, Math.round((Math.min(cap.loadRatioVal, 2.0) / 2.0) * 20));
  const meterStr = "█".repeat(meterBars) + "░".repeat(Math.max(0, 20 - meterBars));

  let text = `🌱 <b>TinyStep 個人成長與產能監控儀表板</b>\n`;
  text += `📅 日期：${todayStr} (${dayName})  |  可支配專注時數：${cap.availableHours} 小時\n`;
  text += `🔥 <b>連續打卡：${streak} 天</b>\n`;
  text += `📊 負荷指標：[${meterStr}] <b>${cap.loadRatio}% (${cap.status})</b>\n`;
  text += `⏱️ 原始預估：${cap.rawMinutes} 分鐘  ➔  校正後總負荷（含阻力與 1.4x 緩衝）：${cap.bufferedMinutes} 分鐘\n`;
  text += `🔄 認知切換耗損：${cap.contextSwitchPenalty} 分鐘  ➔  等效專注總時數：${cap.totalEffectiveHours} 小時\n`;
  text += `🛡️ 70% 可持續餘裕上限：${cap.sustainableLimitHours} 小時 (保留 30% 彈性避免意志力崩潰)\n`;
  text += `───────────────────────────────\n`;

  if (cap.status === "OVERLOAD") {
    text += `⚠️ <b>【警報：嚴重超載】今日預估負荷達 ${cap.loadRatio}%！已觸發規劃謬誤（Planning Fallacy）。</b>\n`;
    text += `💡 《原子習慣》核心策略：與其全盤放棄，不如採取『微步降級（2-Minute Rule）』或『主題日輪替』。\n`;
    text += `👉 建議點擊下方 <b>[⚡ 微步]</b> 啟動兩分鐘定律降級高阻力任務！\n`;
    text += `───────────────────────────────\n`;
  }

  text += `📋 <b>今日任務與身分投票清單 (共 ${tasks.length} 項)：</b>\n\n`;

  if (tasks.length === 0) {
    text += `<i>今日無安排任何任務，好好享受自由時間！</i>\n`;
    return text;
  }

  tasks.forEach((t, idx) => {
    const statusIcon = t.completed ? "✅" : "⏳";
    const downscaleTag = t.is_downscaled ? " <i>(⚡ 微步版)</i>" : "";
    const taskTitle = t.title || t.name || t.id;
    text += `${idx + 1}. ${statusIcon} <b>${taskTitle}</b> (${t.estimated_minutes}m)${downscaleTag}\n`;
    const anchor = t.habit_stack_anchor || t.anchor;
    if (anchor) {
      text += `   ⚓ 錨點：${anchor}\n`;
    }
    const twoMin = t.two_minute_rule || t.downscale_2min;
    if (!t.completed && twoMin) {
      text += `   👉 微步：${twoMin}\n`;
    }
    text += `\n`;
  });

  text += `<i>👉 點擊下方按鈕即可立即打卡或啟動微步降級：</i>`;
  return text;
}

export function renderPlanKeyboard(data) {
  const cap = calculateCapacity(data);
  const tasks = cap.activeTasks;
  const keyboard = [];

  // 為每個未完成的任務提供打卡與微步按鈕
  for (const t of tasks) {
    const taskTitle = t.title || t.name || t.id;
    if (t.completed) {
      keyboard.push([
        { text: `🎉 ${taskTitle} (已完成)`, callback_data: `info:${t.id}` },
        { text: `↩️ 撤銷`, callback_data: `restore:${t.id}` }
      ]);
    } else {
      keyboard.push([
        { text: `✅ 打卡 ${taskTitle}`, callback_data: `check:${t.id}` },
        { text: `⚡ 微步`, callback_data: `downscale:${t.id}` }
      ]);
    }
  }

  // 底部功能按鈕
  keyboard.push([
    { text: "🔄 重新整理", callback_data: "refresh" },
    { text: "🗳️ 身分票箱", callback_data: "identities" },
    { text: "📜 歷史紀錄", callback_data: "history" }
  ]);

  return { inline_keyboard: keyboard };
}

export function renderIdentitiesMessage(data) {
  const identities = data.identities || [];
  const streak = calculateStreak(data);

  let text = `🗳️ <b>身分認同票箱 (Identity Board)</b>\n`;
  text += `🔥 目前連續打卡：<b>${streak} 天</b>\n`;
  text += `───────────────────────────────\n`;

  if (identities.length === 0) {
    text += `<i>目前尚無身分認同資料。</i>\n`;
    return text;
  }

  for (const i of identities) {
    text += `👤 <b>${i.name}</b>  ➔  累計 <b>${i.votes || 0}</b> 票\n`;
    if (i.statement) {
      text += `   <i>「${i.statement}」</i>\n`;
    }
    text += `\n`;
  }

  text += `<i>「每一次行動，都是為你想成為的那種人投下一票。」</i>`;
  return text;
}

export function renderHistoryMessage(data) {
  const history = data.history || {};
  const streak = calculateStreak(data);
  const dates = Object.keys(history).sort().reverse().slice(0, 7);

  let text = `📜 <b>歷史每日打卡紀錄 (近 7 日)</b>\n`;
  text += `🔥 目前連續打卡：<b>${streak} 天</b>\n`;
  text += `───────────────────────────────\n`;

  if (dates.length === 0) {
    text += `<i>目前尚無歷史封存紀錄，明天換日後將自動生成！</i>\n`;
    return text;
  }

  for (const d of dates) {
    const rec = history[d];
    const completedList = (rec.completed || []).join(", ") || "無";
    text += `📅 <b>${d}</b>：${rec.completion_count} / ${rec.total_tasks} 項完成\n`;
    text += `   ✅ 完成：${completedList}\n\n`;
  }

  return text;
}
