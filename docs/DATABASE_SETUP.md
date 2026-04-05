# 資料庫設置指南 - Phase 1

## 📋 概述

本文件說明如何在 Supabase 中設置 Phase 1 所需的資料庫表格。

## 🎯 Phase 1 資料庫需求

Phase 1 需要以下表格：
- ✅ `users` - 用戶表（應該已存在）
- ✅ `trips` - 旅程主表
- ✅ `trip_destinations` - 旅程目的地表

---

## 🚀 快速設置步驟

### 步驟 1：登入 Supabase Dashboard

1. 前往 [Supabase Dashboard](https://app.supabase.com)
2. 選擇你的專案
3. 點擊左側選單的 **Database**
4. 點擊 **SQL Editor**

### 步驟 2：執行 SQL 腳本

1. 在 SQL Editor 中，點擊 **New Query**
2. 複製 `/database/schema.sql` 的完整內容
3. 貼上到 SQL Editor
4. 點擊 **Run** 按鈕執行

### 步驟 3：驗證表格創建成功

在 SQL Editor 中執行：

```sql
-- 檢查表格是否存在
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('users', 'trips', 'trip_destinations');

-- 查看 trips 表結構
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'trips';

-- 查看 trip_destinations 表結構
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'trip_destinations';
```

---

## 📊 資料庫架構說明

### 1. Users 表

```sql
users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    profile_id UUID,
    role_id VARCHAR(50) DEFAULT 'customer',
    is_suspended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
)
```

### 2. Trips 表（Phase 1 核心）

```sql
trips (
    id UUID PRIMARY KEY,
    title VARCHAR(255) NOT NULL,           -- 旅程標題
    description TEXT,                      -- 旅程描述
    start_date DATE,                       -- 開始日期
    end_date DATE,                         -- 結束日期
    owner_id UUID NOT NULL,                -- 擁有者 ID（外鍵到 users）
    status VARCHAR(50) DEFAULT 'planning', -- 狀態
    is_public BOOLEAN DEFAULT FALSE,       -- 是否公開
    cover_image_url TEXT,                  -- 封面圖片
    budget_amount DECIMAL(10, 2),          -- 預算金額
    budget_currency VARCHAR(3),            -- 預算幣別
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
)
```

**狀態值（status）：**
- `planning` - 規劃中
- `ongoing` - 進行中
- `completed` - 已完成
- `cancelled` - 已取消

### 3. Trip Destinations 表

```sql
trip_destinations (
    id UUID PRIMARY KEY,
    trip_id UUID NOT NULL,                 -- 所屬旅程 ID（外鍵到 trips）
    name VARCHAR(255) NOT NULL,            -- 目的地名稱
    description TEXT,                      -- 目的地描述
    address TEXT,                          -- 地址
    latitude DECIMAL(10, 8),               -- 緯度
    longitude DECIMAL(11, 8),              -- 經度
    place_id VARCHAR(255),                 -- Google Places ID（Phase 3）
    visit_date DATE,                       -- 訪問日期
    visit_start_time TIME,                 -- 訪問開始時間
    visit_end_time TIME,                   -- 訪問結束時間
    order_index INTEGER NOT NULL,          -- 訪問順序
    notes TEXT,                            -- 備註
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
)
```

---

## 🔐 Row Level Security (RLS) 策略

資料庫已啟用 Row Level Security，確保用戶只能訪問自己的資料。

### Trips 表的策略

1. **查看權限：** 用戶可以查看自己的旅程或公開的旅程
2. **插入權限：** 用戶只能創建自己擁有的旅程
3. **更新權限：** 用戶只能更新自己的旅程
4. **刪除權限：** 用戶只能刪除自己的旅程

### Trip Destinations 表的策略

1. **查看權限：** 只能查看自己旅程的目的地
2. **插入權限：** 只能為自己的旅程添加目的地
3. **更新權限：** 只能更新自己旅程的目的地
4. **刪除權限：** 只能刪除自己旅程的目的地

---

## 🔄 自動更新 Triggers

資料庫已設置自動觸發器，當更新記錄時自動更新 `updated_at` 欄位。

受影響的表格：
- ✅ users
- ✅ trips
- ✅ trip_destinations

---

## 🧪 測試資料（可選）

如果需要測試資料，可以執行以下 SQL：

```sql
-- 注意：將 'YOUR_USER_ID_HERE' 替換為實際的用戶 ID

-- 創建測試旅程
INSERT INTO trips (title, description, start_date, end_date, owner_id, status)
VALUES
    ('東京7日遊', '櫻花季的東京之旅', '2024-04-01', '2024-04-07', 'YOUR_USER_ID_HERE', 'planning'),
    ('台北週末遊', '美食之旅', '2024-05-15', '2024-05-17', 'YOUR_USER_ID_HERE', 'planning');

-- 獲取剛創建的旅程 ID
SELECT id, title FROM trips WHERE owner_id = 'YOUR_USER_ID_HERE';

-- 為旅程添加目的地（將 'TRIP_ID_HERE' 替換為實際的旅程 ID）
INSERT INTO trip_destinations (trip_id, name, address, order_index)
VALUES
    ('TRIP_ID_HERE', '淺草寺', '東京都台東區淺草2-3-1', 0),
    ('TRIP_ID_HERE', '晴空塔', '東京都墨田區押上1-1-2', 1),
    ('TRIP_ID_HERE', '築地市場', '東京都中央區築地5-2-1', 2);
```

---

## ✅ 驗證 API 可以訪問

設置完成後，可以測試 API：

### 1. 創建旅程

```bash
curl -X POST http://localhost:8000/api/trips \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "測試旅程",
    "description": "這是一個測試旅程",
    "start_date": "2024-06-01",
    "end_date": "2024-06-05",
    "status": "planning"
  }'
```

### 2. 獲取我的旅程列表

```bash
curl -X GET http://localhost:8000/api/trips \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### 3. 添加目的地

```bash
curl -X POST http://localhost:8000/api/trips/{trip_id}/destinations \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "測試目的地",
    "address": "測試地址",
    "order_index": 0
  }'
```

---

## 🐛 常見問題

### Q: RLS 策略導致無法訪問資料？

**A:** 確保你的 Supabase 客戶端使用的是正確的 Auth token。如果使用 Service Role Key，RLS 會被繞過。

### Q: `auth.uid()` 函數返回 NULL？

**A:** 這表示沒有正確的認證 token。檢查：
1. JWT token 是否有效
2. Supabase 客戶端是否正確配置
3. 是否使用了正確的 API key

### Q: 觸發器沒有自動更新 `updated_at`？

**A:** 檢查觸發器是否正確創建：

```sql
SELECT trigger_name, event_object_table, action_statement
FROM information_schema.triggers
WHERE trigger_schema = 'public';
```

---

## 📚 相關文件

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL RLS Guide](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [FastAPI + Supabase Integration](https://supabase.com/docs/guides/api/rest)

---

## 🎉 完成！

資料庫設置完成後，你的 Phase 1 後端就可以開始使用了！

下一步：
1. ✅ 測試 API 端點
2. ✅ 創建前端界面
3. ✅ 開始開發 Phase 2 功能
