// ==========================================
// TinyStep Cloudflare Worker (Standalone Bundle)
// ==========================================

// --- 1. 核心邏輯模組 (Logic) ---
// TinyStep 習慣與產能核心邏輯 (移植自 Python 核心模型)

function getTodayStr(tz = "Asia/Taipei") {
  const now = new Date();
  const formatter = new Intl.DateTimeFormat("en-CA", {
    timeZone: tz,
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  });
  return formatter.format(now); // YYYY-MM-DD
}

function getDayName(tz = "Asia/Taipei") {
  const now = new Date();
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    weekday: "short"
  });
  return formatter.format(now); // Mon, Tue, etc.
}

function checkAndRolloverDay(data, tz = "Asia/Taipei") {
  const todayStr = getTodayStr(tz);
  const lastDate = data.last_date;

  if (!lastDate) {
    data.last_date = todayStr;
    return null;
  }

  if (lastDate !== todayStr) {
    const tasks = data.tasks || [];
    const completedTasks = tasks.filter(t => t.completed).map(t => t.id);
    const downscaledTasks = tasks.filter(t => t.is_downscaled).map(t => t.id);

    if (!data.history) {
      data.history = {};
    }

    data.history[lastDate] = {
      completed: completedTasks,
      downscaled: downscaledTasks,
      completion_count: completedTasks.length,
      total_tasks: tasks.length
    };

    // 重置今日待辦狀態
    for (const t of tasks) {
      t.completed = false;
      t.is_downscaled = false;
      t.completed_at = null;
    }

    data.last_date = todayStr;
    return lastDate;
  }

  return null;
}

function calculateStreak(data, tz = "Asia/Taipei") {
  const tasks = data.tasks || [];
  const history = data.history || {};

  const todayHasCompletion = tasks.some(t => t.completed);
  let streak = todayHasCompletion ? 1 : 0;

  // 往前追溯歷史日期
  const todayStr = getTodayStr(tz);
  let curDate = new Date(todayStr);

  while (true) {
    curDate.setDate(curDate.getDate() - 1);
    const checkDateStr = curDate.toISOString().slice(0, 10);
    const rec = history[checkDateStr];
    if (rec && rec.completed && rec.completed.length > 0) {
      streak += 1;
    } else {
      break;
    }
  }

  return streak;
}

function calculateCapacity(data) {
  const profile = data.profile || {
    daily_focus_hours: 3.5,
    buffer_multiplier: 1.4,
    context_switch_penalty: 15.0,
    sustainable_limit: 0.7
  };

  const tasks = data.tasks || [];
  let rawMinutes = 0;
  let bufferedMinutes = 0;

  for (const t of tasks) {
    const mins = t.estimated_minutes || 25;
    const friction = t.cognitive_friction || 1.2;
    rawMinutes += mins;
    bufferedMinutes += mins * friction * profile.buffer_multiplier;
  }

  const penalty = tasks.length * profile.context_switch_penalty;
  const totalEffectiveMinutes = bufferedMinutes + penalty;
  const availableMinutes = profile.daily_focus_hours * 60;
  const loadRatio = availableMinutes > 0 ? totalEffectiveMinutes / availableMinutes : 0;

  let status = "OPTIMAL";
  if (loadRatio > 1.0) {
    status = "OVERLOAD";
  } else if (loadRatio > profile.sustainable_limit) {
    status = "WARNING";
  }

  return {
    rawMinutes: Math.round(rawMinutes),
    bufferedMinutes: Math.round(bufferedMinutes),
    contextSwitchPenalty: Math.round(penalty),
    totalEffectiveMinutes: Math.round(totalEffectiveMinutes),
    totalEffectiveHours: (totalEffectiveMinutes / 60).toFixed(1),
    availableHours: profile.daily_focus_hours,
    sustainableLimitHours: (profile.daily_focus_hours * profile.sustainable_limit).toFixed(1),
    loadRatio: Math.round(loadRatio * 100),
    status
  };
}

function checkTask(data, taskId) {
  const tasks = data.tasks || [];
  const identities = data.identities || [];
  const task = tasks.find(t => t.id === taskId);
  if (!task) return null;

  task.completed = true;
  task.completed_at = new Date().toISOString();

  // 為對應身分認同投票 +1
  const iden = identities.find(i => i.id === task.identity_id);
  if (iden) {
    iden.votes = (iden.votes || 0) + 1;
  }

  return { task, identity: iden };
}

function downscaleTask(data, taskId) {
  const tasks = data.tasks || [];
  const identities = data.identities || [];
  const task = tasks.find(t => t.id === taskId);
  if (!task) return null;

  task.is_downscaled = true;
  task.completed = true;
  task.completed_at = new Date().toISOString();

  const iden = identities.find(i => i.id === task.identity_id);
  if (iden) {
    iden.votes = (iden.votes || 0) + 1;
  }

  return { task, identity: iden };
}

function restoreTask(data, taskId) {
  const tasks = data.tasks || [];
  const identities = data.identities || [];
  const task = tasks.find(t => t.id === taskId);
  if (!task) return null;

  if (task.completed) {
    const iden = identities.find(i => i.id === task.identity_id);
    if (iden && iden.votes > 0) {
      iden.votes -= 1;
    }
  }

  task.completed = false;
  task.is_downscaled = false;
  task.completed_at = null;

  return task;
}


// --- 2. 視覺排版與按鈕模組 (Render) ---
// 訊息視覺化與 Telegram 行內按鈕 (Inline Keyboard) 格式化


function renderPlanMessage(data) {
  const todayStr = getTodayStr();
  const dayName = getDayName();
  const streak = calculateStreak(data);
  const cap = calculateCapacity(data);
  const tasks = data.tasks || [];

  const meterBars = Math.min(20, Math.round((cap.loadRatio / 100) * 20));
  const meterStr = "█".repeat(meterBars) + "░".repeat(Math.max(0, 20 - meterBars));

  let text = `🌱 <b>TinyStep 個人成長與產能監控儀表板</b>\n`;
  text += `📅 日期：${todayStr} (${dayName})  |  可支配：${cap.availableHours} 小時\n`;
  text += `🔥 <b>連續打卡：${streak} 天</b>\n`;
  text += `📊 負荷指標：[${meterStr}] <b>${cap.loadRatio}% (${cap.status})</b>\n`;
  text += `⏱️ 校正負荷：${cap.bufferedMinutes} 分鐘  ➔  等效耗時：${cap.totalEffectiveHours} 小時\n`;
  text += `🛡️ 70% 可持續上限：${cap.sustainableLimitHours} 小時 (保留 30% 彈性避免意志力透支)\n`;
  text += `───────────────────────────────\n`;

  if (cap.status === "OVERLOAD") {
    text += `⚠️ <b>【警報：超載】今日負荷達 ${cap.loadRatio}%！</b>\n`;
    text += `💡 建議點擊 <b>[⚡ 微步]</b> 啟動兩分鐘定律降級！\n`;
    text += `───────────────────────────────\n`;
  }

  text += `📋 <b>今日任務與身分投票清單 (共 ${tasks.length} 項)：</b>\n\n`;

  if (tasks.length === 0) {
    text += `<i>目前尚無任何習慣任務。請於 Mac 執行 <code>tinystep add</code> 新增！</i>\n`;
    return text;
  }

  tasks.forEach((t, idx) => {
    const statusIcon = t.completed ? "✅" : "⏳";
    const downscaleTag = t.is_downscaled ? " <i>(⚡ 微步版)</i>" : "";
    text += `${idx + 1}. ${statusIcon} <b>${t.name}</b> (${t.estimated_minutes}m)${downscaleTag}\n`;
    if (t.anchor) {
      text += `   ⚓ 錨點：${t.anchor}\n`;
    }
    if (!t.completed && t.downscale_2min) {
      text += `   👉 微步：${t.downscale_2min}\n`;
    }
    text += `\n`;
  });

  text += `<i>👉 點擊下方按鈕即可立即打卡或啟動微步降級：</i>`;
  return text;
}

function renderPlanKeyboard(data) {
  const tasks = data.tasks || [];
  const keyboard = [];

  // 為每個未完成的任務提供打卡與微步按鈕
  for (const t of tasks) {
    if (t.completed) {
      keyboard.push([
        { text: `🎉 ${t.name} (已完成)`, callback_data: `info:${t.id}` },
        { text: `↩️ 撤銷`, callback_data: `restore:${t.id}` }
      ]);
    } else {
      keyboard.push([
        { text: `✅ 打卡 ${t.name}`, callback_data: `check:${t.id}` },
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

function renderIdentitiesMessage(data) {
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

function renderHistoryMessage(data) {
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

// --- 3. Telegram API 通訊模組 (Telegram) ---
// Telegram Bot API 通訊模組

const API_BASE = "https://api.telegram.org/bot";

async function sendMessage(botToken, chatId, text, replyMarkup = null) {
  const url = `${API_BASE}${botToken}/sendMessage`;
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: "HTML"
  };
  if (replyMarkup) {
    body.reply_markup = replyMarkup;
  }

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return await res.json();
}

async function editMessageText(botToken, chatId, messageId, text, replyMarkup = null) {
  const url = `${API_BASE}${botToken}/editMessageText`;
  const body = {
    chat_id: chatId,
    message_id: messageId,
    text: text,
    parse_mode: "HTML"
  };
  if (replyMarkup) {
    body.reply_markup = replyMarkup;
  }

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return await res.json();
}

async function answerCallbackQuery(botToken, callbackQueryId, text = "", showAlert = false) {
  const url = `${API_BASE}${botToken}/answerCallbackQuery`;
  const body = {
    callback_query_id: callbackQueryId,
    text: text,
    show_alert: showAlert
  };

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return await res.json();
}

async function setWebhook(botToken, webhookUrl, secretToken = null) {
  const url = `${API_BASE}${botToken}/setWebhook`;
  const body = {
    url: webhookUrl
  };
  if (secretToken) {
    body.secret_token = secretToken;
  }

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return await res.json();
}


// --- 4. 主服務入口 (Main Worker Handler) ---
// TinyStep Cloudflare Worker 主服務入口
// 支援 Telegram Webhook、REST API 同步與晨間定時 Cron 推播


const DEFAULT_DATA = {
  profile: {
    daily_focus_hours: 3.5,
    buffer_multiplier: 1.4,
    context_switch_penalty: 15.0,
    sustainable_limit: 0.7
  },
  last_date: "",
  identities: [],
  tasks: [],
  history: {}
};

async function loadData(kv) {
  const raw = await kv.get("data.json");
  if (!raw) {
    return JSON.parse(JSON.stringify(DEFAULT_DATA));
  }
  try {
    return JSON.parse(raw);
  } catch (e) {
    return JSON.parse(JSON.stringify(DEFAULT_DATA));
  }
}

async function saveData(kv, data) {
  await kv.put("data.json", JSON.stringify(data, null, 2));
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const botToken = env.TELEGRAM_BOT_TOKEN;
    const allowedChatId = String(env.ALLOWED_CHAT_ID || "");
    const syncToken = env.SYNC_TOKEN || "";

    // 1. Telegram Webhook 接收端
    if (request.method === "POST" && url.pathname === "/webhook") {
      let update;
      try {
        update = await request.json();
      } catch (e) {
        return new Response("Invalid JSON", { status: 400 });
      }

      // 檢查 Telegram Update
      if (update.message) {
        const msg = update.message;
        const chatId = String(msg.chat.id);
        const fromId = String(msg.from?.id || "");

        // 隱私白名單驗證
        if (allowedChatId && chatId !== allowedChatId && fromId !== allowedChatId) {
          await sendMessage(botToken, chatId, "⛔ 抱歉，此 TinyStep 機器人僅限擁有者私密使用。");
          return new Response("OK");
        }

        const text = (msg.text || "").trim();
        const data = await loadData(env.TINYSTEP_KV);
        checkAndRolloverDay(data);
        await saveData(env.TINYSTEP_KV, data);

        if (text === "/start" || text === "/help") {
          const welcome = `🌱 <b>歡迎使用 TinyStep 原子習慣機器人！</b>\n\n` +
            `隨時隨地用手機為你的理想身分投下一票。\n\n` +
            `<b>可用指令：</b>\n` +
            `• /plan - 檢視今日計畫與互動打卡按鈕\n` +
            `• /identities - 檢視身分認同得票箱\n` +
            `• /history - 檢視歷史連續打卡紀錄\n` +
            `• /check &lt;id&gt; - 完成指定任務\n` +
            `• /downscale &lt;id&gt; - 啟動兩分鐘微步降級\n\n` +
            `<i>輸入 /plan 即可展開今日儀表板！</i>`;
          await sendMessage(botToken, chatId, welcome);
        } else if (text === "/plan") {
          const planText = renderPlanMessage(data);
          const keyboard = renderPlanKeyboard(data);
          await sendMessage(botToken, chatId, planText, keyboard);
        } else if (text === "/identities") {
          const idenText = renderIdentitiesMessage(data);
          const keyboard = {
            inline_keyboard: [[{ text: "⬅️ 返回今日計畫", callback_data: "back_to_plan" }]]
          };
          await sendMessage(botToken, chatId, idenText, keyboard);
        } else if (text === "/history") {
          const histText = renderHistoryMessage(data);
          const keyboard = {
            inline_keyboard: [[{ text: "⬅️ 返回今日計畫", callback_data: "back_to_plan" }]]
          };
          await sendMessage(botToken, chatId, histText, keyboard);
        } else if (text.startsWith("/check ")) {
          const taskId = text.replace("/check ", "").trim();
          const res = checkTask(data, taskId);
          if (res) {
            await saveData(env.TINYSTEP_KV, data);
            await sendMessage(botToken, chatId, `🎉 任務 <b>${res.task.name}</b> 已打卡完成！\n為【${res.identity ? res.identity.name : "理想身分"}】投下一票！`);
          } else {
            await sendMessage(botToken, chatId, `❌ 找不到任務 ID: <code>${taskId}</code>`);
          }
        } else if (text.startsWith("/downscale ")) {
          const taskId = text.replace("/downscale ", "").trim();
          const res = downscaleTask(data, taskId);
          if (res) {
            await saveData(env.TINYSTEP_KV, data);
            await sendMessage(botToken, chatId, `⚡ 任務 <b>${res.task.name}</b> 已微步降級打卡！\n絕不連續中斷兩次！為【${res.identity ? res.identity.name : "理想身分"}】投下堅定的一票！`);
          } else {
            await sendMessage(botToken, chatId, `❌ 找不到任務 ID: <code>${taskId}</code>`);
          }
        }
      }

      // 處理 Telegram 行內按鈕點擊 (Callback Query)
      if (update.callback_query) {
        const query = update.callback_query;
        const fromId = String(query.from?.id || "");
        const msg = query.message;
        const chatId = String(msg.chat.id);
        const messageId = msg.message_id;
        const actionData = query.data || "";

        if (allowedChatId && fromId !== allowedChatId) {
          await answerCallbackQuery(botToken, query.id, "⛔ 無操作權限", true);
          return new Response("OK");
        }

        const data = await loadData(env.TINYSTEP_KV);
        checkAndRolloverDay(data);

        if (actionData.startsWith("check:")) {
          const taskId = actionData.split(":")[1];
          const res = checkTask(data, taskId);
          await saveData(env.TINYSTEP_KV, data);

          const toast = res ? `🎉 ${res.task.name} 已完成打卡！` : "找不到任務";
          await answerCallbackQuery(botToken, query.id, toast);

          // 原地刷新卡片
          const newText = renderPlanMessage(data);
          const newKeyboard = renderPlanKeyboard(data);
          await editMessageText(botToken, chatId, messageId, newText, newKeyboard);
        } else if (actionData.startsWith("downscale:")) {
          const taskId = actionData.split(":")[1];
          const res = downscaleTask(data, taskId);
          await saveData(env.TINYSTEP_KV, data);

          const toast = res ? `⚡ ${res.task.name} 已啟動微步降級！` : "找不到任務";
          await answerCallbackQuery(botToken, query.id, toast);

          const newText = renderPlanMessage(data);
          const newKeyboard = renderPlanKeyboard(data);
          await editMessageText(botToken, chatId, messageId, newText, newKeyboard);
        } else if (actionData.startsWith("restore:")) {
          const taskId = actionData.split(":")[1];
          restoreTask(data, taskId);
          await saveData(env.TINYSTEP_KV, data);

          await answerCallbackQuery(botToken, query.id, "已撤銷打卡狀態");
          const newText = renderPlanMessage(data);
          const newKeyboard = renderPlanKeyboard(data);
          await editMessageText(botToken, chatId, messageId, newText, newKeyboard);
        } else if (actionData.startsWith("info:")) {
          const taskId = actionData.split(":")[1];
          const t = (data.tasks || []).find(item => item.id === taskId);
          const info = t ? `✅「${t.name}」今日已打卡完成！` : "已完成";
          await answerCallbackQuery(botToken, query.id, info, false);
        } else if (actionData === "refresh" || actionData === "back_to_plan") {
          await answerCallbackQuery(botToken, query.id, "已重新整理");
          const newText = renderPlanMessage(data);
          const newKeyboard = renderPlanKeyboard(data);
          await editMessageText(botToken, chatId, messageId, newText, newKeyboard);
        } else if (actionData === "identities") {
          await answerCallbackQuery(botToken, query.id);
          const idenText = renderIdentitiesMessage(data);
          const keyboard = {
            inline_keyboard: [[{ text: "⬅️ 返回今日計畫", callback_data: "back_to_plan" }]]
          };
          await editMessageText(botToken, chatId, messageId, idenText, keyboard);
        } else if (actionData === "history") {
          await answerCallbackQuery(botToken, query.id);
          const histText = renderHistoryMessage(data);
          const keyboard = {
            inline_keyboard: [[{ text: "⬅️ 返回今日計畫", callback_data: "back_to_plan" }]]
          };
          await editMessageText(botToken, chatId, messageId, histText, keyboard);
        }

        return new Response("OK");
      }

      return new Response("OK");
    }

    // 2. Mac CLI 雲端雙向同步 REST API (GET / POST /api/sync)
    if (url.pathname === "/api/sync") {
      const authHeader = request.headers.get("Authorization") || "";
      const token = authHeader.replace("Bearer ", "").trim();

      if (syncToken && token !== syncToken) {
        return new Response(JSON.stringify({ error: "Unauthorized" }), {
          status: 401,
          headers: { "Content-Type": "application/json" }
        });
      }

      if (request.method === "GET") {
        const data = await loadData(env.TINYSTEP_KV);
        checkAndRolloverDay(data);
        await saveData(env.TINYSTEP_KV, data);
        return new Response(JSON.stringify(data), {
          status: 200,
          headers: { "Content-Type": "application/json" }
        });
      }

      if (request.method === "POST") {
        let payload;
        try {
          payload = await request.json();
        } catch (e) {
          return new Response(JSON.stringify({ error: "Invalid JSON" }), { status: 400 });
        }

        if (payload && typeof payload === "object") {
          await saveData(env.TINYSTEP_KV, payload);
          return new Response(JSON.stringify({ status: "success", message: "Data synced successfully" }), {
            status: 200,
            headers: { "Content-Type": "application/json" }
          });
        }
      }
    }

    // 3. 一鍵註冊 Webhook 輔助端點
    if (url.pathname === "/set-webhook") {
      const host = url.origin;
      const webhookUrl = `${host}/webhook`;
      const res = await setWebhook(botToken, webhookUrl);
      return new Response(JSON.stringify(res, null, 2), {
        status: 200,
        headers: { "Content-Type": "application/json" }
      });
    }

    // 4. 首頁健康檢查
    if (url.pathname === "/") {
      return new Response("🌱 TinyStep Cloudflare Worker & Telegram Bot is running smoothly!", {
        headers: { "Content-Type": "text/plain; charset=utf-8" }
      });
    }

    return new Response("Not Found", { status: 404 });
  },

  // 5. 每日晨間定時 Cron 觸發 (每日 08:00 AM 台灣時間)
  async scheduled(event, env, ctx) {
    const botToken = env.TELEGRAM_BOT_TOKEN;
    const allowedChatId = env.ALLOWED_CHAT_ID;
    if (!botToken || !allowedChatId) return;

    const data = await loadData(env.TINYSTEP_KV);
    checkAndRolloverDay(data);
    await saveData(env.TINYSTEP_KV, data);

    const planText = `🌅 <b>早安！新的一天開始了。</b>\n` + renderPlanMessage(data);
    const keyboard = renderPlanKeyboard(data);

    await sendMessage(botToken, allowedChatId, planText, keyboard);
  }
};
