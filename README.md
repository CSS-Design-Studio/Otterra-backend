# Solotrip Backend (FastAPI)

基於 FastAPI + Supabase 的後端 API 服務，參考 Spring Boot 配置方式，支援多環境部署。

## 快速開始

### 1. 安裝依賴

```bash
pip install -r requirements.txt
```

### 2. 配置環境

```bash
# 複製配置範本
cp config/.env.example config/.env.local

# 編輯配置檔，填入你的 Supabase 憑證
nano config/.env.local
```

### 3. 啟動服務

```bash
# 本地開發（預設）
./run.sh

# 或指定環境
./run.sh local   # 本地開發
./run.sh dev     # 測試環境
./run.sh prod    # 正式環境
```

## 專案結構

```
solotrip-fastapi/
├── .env                    # 主配置（環境切換）✅ 可提交
├── .gitignore              # Git 忽略規則
├── run.sh                  # 啟動腳本
├── requirements.txt        # Python 依賴
│
├── config/                 # 環境配置目錄
│   ├── .env.example       # 配置範本 ✅ 可提交
│   ├── .env.local         # 本地開發 ❌ 敏感資訊
│   ├── .env.dev           # 測試環境 ❌ 敏感資訊
│   └── .env.prod          # 正式環境 ❌ 敏感資訊
│
├── app/                    # 應用程式主目錄
│   ├── main.py            # FastAPI 應用入口
│   ├── api/               # API 路由
│   │   └── routes/        # 路由模組
│   ├── core/              # 核心模組
│   │   ├── config.py      # 配置管理
│   │   └── security.py    # 安全相關（JWT 等）
│   ├── db/                # 資料庫
│   │   ├── supabase.py    # Supabase 客戶端
│   │   └── redis.py       # Redis 客戶端（可選）
│   ├── models/            # 資料模型
│   ├── schemas/           # Pydantic Schemas
│   ├── services/          # 業務邏輯
│   └── utils/             # 工具函式
│
├── tests/                  # 測試
└── docs/                   # 文件
    ├── ENVIRONMENTS.md    # 環境配置說明
    └── REDIS_SETUP.md     # Redis 設置指南
```

## 環境說明

| 環境 | 用途 | 配置檔 | 啟動方式 |
|------|------|--------|----------|
| **local** | 本地開發 | `config/.env.local` | `./run.sh` |
| **dev** | 測試環境 | `config/.env.dev` | `./run.sh dev` |
| **prod** | 正式環境 | `config/.env.prod` | `./run.sh prod` |

## 技術棧

- **框架**: FastAPI 0.115.4
- **資料庫**: Supabase (PostgreSQL)
- **快取**: Redis (可選)
- **認證**: JWT
- **部署**: Uvicorn

## 主要功能

### Phase 1 - 基礎功能（已完成 ✅）

- ✅ 用戶註冊與登入
- ✅ JWT 身份驗證與授權
- ✅ 旅程管理（創建、編輯、刪除、查詢）
- ✅ 目的地管理（添加、編輯、刪除）
- ✅ 權限控制（用戶只能管理自己的旅程）
- ✅ 分頁查詢與篩選

### 技術特性

- ✅ 多環境配置管理
- ✅ Supabase 資料庫整合
- ✅ Row Level Security (RLS)
- ✅ Redis 快取支援（可選）
- ✅ 完整的依賴注入系統
- ✅ API 文件自動生成（FastAPI）
- ✅ 三層架構設計

## API 文件

啟動服務後訪問：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 快速開始指南

### 📋 Phase 1 設置（新用戶必讀）

1. **設置資料庫：** 參考 [資料庫設置指南](docs/DATABASE_SETUP.md)
2. **API 測試：** 查看 [Phase 1 完成總結](docs/PHASE1_COMPLETE.md)
3. **API 文件：** 訪問 http://localhost:8000/docs

## 開發指南

### 環境切換原理

1. **主配置 `.env`**: 只包含 `ENV=local`，指定當前環境
2. **啟動腳本 `run.sh`**: 接受環境參數，更新 `.env` 的 ENV 值
3. **配置載入 `config.py`**: 根據 ENV 值載入 `config/.env.{ENV}`

### 添加新的配置項

1. 在 `config/.env.example` 添加配置項
2. 在 `app/core/config.py` 的 `Settings` 類添加對應欄位
3. 在各環境配置檔 (`config/.env.*`) 填入實際值

### Redis 使用

詳見 `REDIS_SETUP.md`

- 本地開發：可選（預設關閉）
- 測試環境：建議啟用
- 正式環境：必須啟用

## 部署

### Docker

```bash
# TODO: 添加 Dockerfile
```

### 雲端平台

- Railway
- Render
- AWS / GCP / Azure

## 貢獻指南

1. Fork 專案
2. 創建分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. Push 到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 授權

[MIT License](LICENSE)

## 聯絡方式

- 專案連結: [GitHub](https://github.com/yourusername/solotrip-fastapi)
