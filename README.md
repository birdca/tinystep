# 🌱 TinyStep: 開源原子習慣與產能調控 Agent

> **「你不會達到目標的高度，而是會跌落至系統的底線。」**  
> ——《原子習慣》（Atomic Habits）

**TinyStep** 是一個專為個人成長、產能調控與過度預估計算打造的開源 CLI Agent。  
它結合了《原子習慣》的行為改變四法則（顯而易見、誘人吸引、輕而易舉、令人滿足）、身分認同投票模型，以及認知科學中的**規劃謬誤（Planning Fallacy）校正引擎**，防止使用者陷入「目標訂太滿 ➔ 兩週後崩潰放棄」的常見陷阱。

---

## ✨ 核心特性

1. **身分認同優先（Identity-First）**：每一次完成打卡，都是為你想成為的那種人投下一票。
2. **規劃謬誤與過度預估計算（Capacity Engine）**：
   * 自動導入霍夫施塔特定律膨脹係數（$1.4\times$）與任務認知阻力加權。
   * 自動加計跨領域任務情境切換耗損（每項 15 分鐘冷卻）。
   * 嚴格落實 **70% 可持續餘裕原則**，保留 30% 彈性避免意志力透支。
3. **兩分鐘定律微步降級（The 2-Minute Rule）**：
   * 當今日負荷過高或狀態不佳時，一鍵將任務降級至「2分鐘微啟動版本」，維持「絕不連續錯過兩次」防線。
4. **完全離線、注重隱私與可重置性**：
   * 所有設定與數據儲存在本機 `~/.tinystep/data.json`。
   * 隨時可透過 `tinystep clear` 一鍵恢復全新乾淨開局，或透過 `export` / `import` 分享範本。

---

## 🚀 快速開始 (Quick Start)

### 1. 安裝
```bash
git clone https://github.com/your-username/tinystep.git
cd tinystep
pip install -e .
```

### 2. 初始化系統
安裝完成後，你可以選擇全新空白開局，或套用範本：

```bash
# 全新乾淨開局
tinystep init

# 或套用範本：
tinystep init --template general             # 一般自律生活 (閱讀/運動/反思)
```

---

## 🛠️ 指令手冊 (Command Reference)

| 指令 | 說明 | 範例 |
| :--- | :--- | :--- |
| `tinystep plan` | 檢視今日計畫、負荷儀表板與調度建言 | `tinystep plan` / `tinystep plan --hours 4.0` |
| `tinystep check <ID>` | 完成打卡並為對應理想身分投下一票 | `tinystep check reading` |
| `tinystep downscale <ID>` | 啟動兩分鐘定律微步降級（降低阻力保護打卡） | `tinystep downscale reading` |
| `tinystep restore <ID>` | 恢復為完整常規任務時間 | `tinystep restore reading` |
| `tinystep stack` | 檢視今日習慣堆疊錨點鏈（讓提示顯而易見） | `tinystep stack` |
| `tinystep identities` | 檢視身分認同票箱累積狀況 | `tinystep identities` |
| `tinystep audit` | 動態分析當前任務清單之過度預估風險報告 | `tinystep audit` |
| `tinystep add` | 新增自訂任務 | `tinystep add code_kata "練習 1 題演算法" --minutes 30` |
| `tinystep remove <ID>` | 刪除指定任務 | `tinystep remove code_kata` |
| `tinystep add-identity` | 新增理想身分認同宣言 | `tinystep add-identity writer "作家"` |
| `tinystep remove-identity`| 刪除指定身分代號 | `tinystep remove-identity writer` |
| `tinystep clear` | **清空所有個人化目標與身分（回到全新出廠狀態）** | `tinystep clear -f` |
| `tinystep reset` | 重置今日打卡狀態（新的一天開始） | `tinystep reset` |
| `tinystep export <file>` | 匯出目前習慣設定為 JSON 檔 | `tinystep export my_habits.json` |
| `tinystep import <file>` | 從 JSON 檔案匯入習慣設定 | `tinystep import my_habits.json` |

---

## 📂 範本管理 (Examples & Templates)

專案中的 `examples/` 資料夾內建多種開源習慣範本供參考或載入：
* [`examples/general.json`](examples/general.json)：適合生活、閱讀、運動與反思。

---

## 📄 開源許可 (License)

MIT License. 歡迎 Fork、貢獻與擴充！
