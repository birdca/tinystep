// TinyStep Cloudflare Worker 主服務入口
// 支援 Telegram Webhook、REST API 同步與晨間定時 Cron 推播

import { checkAndRolloverDay, checkTask, downscaleTask, restoreTask } from "./logic.js";
import { renderPlanMessage, renderPlanKeyboard, renderIdentitiesMessage, renderHistoryMessage } from "./render.js";
import { sendMessage, editMessageText, answerCallbackQuery, setWebhook } from "./telegram.js";

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
            await sendMessage(botToken, chatId, `🎉 任務 <b>${(res.task.title || res.task.name || res.task.id)}</b> 已打卡完成！\n為【${res.identity ? res.identity.name : "理想身分"}】投下一票！`);
          } else {
            await sendMessage(botToken, chatId, `❌ 找不到任務 ID: <code>${taskId}</code>`);
          }
        } else if (text.startsWith("/downscale ")) {
          const taskId = text.replace("/downscale ", "").trim();
          const res = downscaleTask(data, taskId);
          if (res) {
            await saveData(env.TINYSTEP_KV, data);
            await sendMessage(botToken, chatId, `⚡ 任務 <b>${(res.task.title || res.task.name || res.task.id)}</b> 已微步降級打卡！\n絕不連續中斷兩次！為【${res.identity ? res.identity.name : "理想身分"}】投下堅定的一票！`);
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

          const toast = res ? `🎉 ${(res.task.title || res.task.name || res.task.id)} 已完成打卡！` : "找不到任務";
          await answerCallbackQuery(botToken, query.id, toast);

          // 原地刷新卡片
          const newText = renderPlanMessage(data);
          const newKeyboard = renderPlanKeyboard(data);
          await editMessageText(botToken, chatId, messageId, newText, newKeyboard);
        } else if (actionData.startsWith("downscale:")) {
          const taskId = actionData.split(":")[1];
          const res = downscaleTask(data, taskId);
          await saveData(env.TINYSTEP_KV, data);

          const toast = res ? `⚡ ${(res.task.title || res.task.name || res.task.id)} 已啟動微步降級！` : "找不到任務";
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
          const info = t ? `✅「${(t.title || t.name || t.id)}」今日已打卡完成！` : "已完成";
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
