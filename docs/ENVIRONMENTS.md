# 環境配置說明

本專案參考 Spring Boot 的配置方式，支援多環境部署，適合從開發到上架 App Store 的完整流程。

## 專案結構

```
solotrip-fastapi/
├── .env                    # 主配置檔（只用來切換環境）✅ 可提交
├── run.sh                  # 單一啟動腳本
├── config/
│   ├── .env.example       # 配置範本 ✅ 可提交
│   ├── .env.local         # 本地開發配置 ❌ 不提交
│   ├── .env.dev           # 測試環境配置 ❌ 不提交
│   └── .env.prod          # 正式環境配置 ❌ 不提交
└── app/
    └── core/
        └── config.py      # 配置載入邏輯
```

## 環境說明

### 1. Local（本地開發）
- 用途：開發者本機測試
- 配置檔：`config/.env.local`
- 啟動：`./run.sh` 或 `./run.sh local`
- 特點：Debug 模式開啟、可使用測試資料、Redis 可關閉

### 2. Dev（開發/測試環境）
- 用途：團隊協作測試、QA 測試
- 配置檔：`config/.env.dev`
- 啟動：`./run.sh dev`
- 特點：使用測試資料庫、測試 API keys、Redis 建議啟用

### 3. Production（正式環境）
- 用途：App Store 上架後的正式環境
- 配置檔：`config/.env.prod`
- 啟動：`./run.sh prod`
- 特點：正式資料庫、正式 API keys、多 worker、Debug 關閉、Redis 必須啟用

## 使用步驟

### 1. 複製範例配置
```bash
# 根據你的環境複製對應的配置檔
cp config/.env.example config/.env.local
# 然後編輯 config/.env.local 填入你的設定
```

### 2. 填入對應環境的設定

**本地開發 (config/.env.local)**
- 使用 Supabase 開發專案
- JWT_SECRET 可用簡單的值
- 第三方服務用測試 keys
- REDIS_ENABLED=false（可選）

**正式環境 (config/.env.prod)**
- 使用 Supabase 正式專案
- JWT_SECRET 必須用強密碼
- 第三方服務用正式 keys
- DEBUG=false
- REDIS_ENABLED=true（必須）

### 3. 啟動應用

```bash
# 本地開發（預設）
./run.sh

# 測試環境
./run.sh dev

# 正式環境（部署到伺服器時）
./run.sh prod
```

## 環境切換原理

1. **主配置檔 `.env`**：只包含一行 `ENV=local`，用來指定當前環境
2. **run.sh 腳本**：接受環境參數，自動更新 `.env` 中的 ENV 值
3. **config.py**：讀取 `.env` 的 ENV 值，載入對應的 `config/.env.{ENV}` 配置檔

## 安全注意事項

⚠️ **重要：絕對不要將 .env.* 檔案提交到 Git！**

- `.env.*` 已加入 `.gitignore`
- 只提交 `.env.example` 作為範本
- 每個環境的敏感資訊（API keys、secrets）都不同
- 正式環境的配置應存放在安全的密碼管理工具

## App Store 上架流程

1. **開發階段**：使用 `.env.local`
2. **內部測試**：使用 `.env.dev`
3. **TestFlight 測試**：可使用 `.env.dev` 或獨立的 staging 環境
4. **正式上架**：使用 `.env.prod`

## 環境變數說明

| 變數 | 說明 | Local | Dev | Prod |
|------|------|-------|-----|------|
| ENV | 環境名稱 | local | dev | production |
| DEBUG | 除錯模式 | true | true | false |
| SUPABASE_URL | Supabase 專案 URL | 開發專案 | 測試專案 | 正式專案 |
| SUPABASE_ANON_KEY | Supabase Anon Key | 開發 key | 測試 key | 正式 key |
| JWT_SECRET | JWT 加密密鑰 | 簡單值 | 測試值 | 強密碼 |
