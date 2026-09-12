// Telegram Bot API 通訊模組

const API_BASE = "https://api.telegram.org/bot";

export async function sendMessage(botToken, chatId, text, replyMarkup = null) {
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

export async function editMessageText(botToken, chatId, messageId, text, replyMarkup = null) {
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

export async function answerCallbackQuery(botToken, callbackQueryId, text = "", showAlert = false) {
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

export async function setWebhook(botToken, webhookUrl, secretToken = null) {
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
