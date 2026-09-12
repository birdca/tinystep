# 🌱 TinyStep Cloudflare Worker & Telegram Bot

這是一個專為 **TinyStep** 設計的 Serverless 雲端打卡機器人與同步服務。
* **100% 免費**：運行在 Cloudflare Workers (免費版每日 10 萬次請求) 與 Cloudflare KV。
* **電腦無需開機**：手機 24 小時隨時在 Telegram 點按鈕打卡。
* **雙向無縫同步**：Mac 終端機與手機進度完全一致。
* **晨間自動推播**：每日 08:00 AM (台灣時間) 自動發布今日計畫與按鈕。

---

## 🚀 3 分鐘部署步驟

### 步驟 1：建立免費 KV 資料庫
在終端機進入 `serverless/` 目錄，執行：
```bash
npx wrangler kv namespace create TINYSTEP_KV
```
終端機會輸出類似如下的資訊：
```text
[[kv_namespaces]]
binding = "TINYSTEP_KV"
id = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```
請將輸出的 `id` 複製，並貼入 `serverless/wrangler.toml` 中的 `id = "..."`。

---

### 步驟 2：設定敏感金鑰 (Secrets)
執行以下三個指令設定金鑰：

1. **設定 Telegram Bot Token**：
   ```bash
   npx wrangler secret put TELEGRAM_BOT_TOKEN
   ```
   *(貼上從 @BotFather 取得的 Token)*

2. **設定你的 Telegram Chat ID (白名單防護)**：
   ```bash
   npx wrangler secret put ALLOWED_CHAT_ID
   ```
   *(貼上你的 Chat ID)*

3. **設定 Mac 同步金鑰 (自訂一段密碼即可)**：
   ```bash
   npx wrangler secret put SYNC_TOKEN
   ```
   *(隨意輸入一段高強度密碼，例如 tinystep_secret_2026)*

---

### 步驟 3：一鍵部署至 Cloudflare
```bash
npx wrangler deploy
```
部署完成後，Wrangler 會提供你的 Worker 網址，例如：
`https://tinystep-bot.<your-subdomain>.workers.dev`

---

### 步驟 4：綁定 Telegram Webhook
部署完成後，只要在瀏覽器打開（或用 curl 請求）以下網址即可完成 Telegram 註冊：
```bash
curl https://tinystep-bot.<your-subdomain>.workers.dev/set-webhook
```
若看到 `{"ok": true, "result": true, "description": "Webhook was set"}` 即代表串接成功！

---

### 步驟 5：Mac 端同步設定
在 Mac 終端機執行：
```bash
tinystep config --sync-url https://tinystep-bot.<your-subdomain>.workers.dev --token <你的_SYNC_TOKEN>
tinystep sync --push
```
現在，你的 Mac 與手機 Telegram 已經完全同步！
