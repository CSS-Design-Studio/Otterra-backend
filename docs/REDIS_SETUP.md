# Redis 設置指南

## Redis 是什麼？用途是什麼？

Redis 是一個記憶體快取資料庫，在本專案中用於：

1. **驗證碼存儲**：手機/Email 驗證碼（有效期 5-10 分鐘）
2. **API 限流**：防止 API 被惡意呼叫
3. **資料快取**：熱門資料快取，減少資料庫查詢
4. **Session 管理**：用戶登入 token 黑名單

## 是否需要 Redis？

| 環境 | 是否需要 | 說明 |
|------|---------|------|
| **本地開發** | ❌ 可選 | 大部分功能不需要，除非要測試驗證碼 |
| **測試環境** | ✅ 建議 | 完整測試功能 |
| **正式環境** | ✅ 必須 | App Store 上架後必須啟用 |

## 本地安裝 Redis

### 方法 1：Docker（推薦）

最簡單的方式，不需要安裝到系統：

```bash
# 啟動 Redis（背景執行）
docker run -d \
  --name solotrip-redis \
  -p 6379:6379 \
  redis:7-alpine

# 查看狀態
docker ps | grep redis

# 停止 Redis
docker stop solotrip-redis

# 重新啟動
docker start solotrip-redis
```

### 方法 2：直接安裝

**Ubuntu/Debian：**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**macOS：**
```bash
brew install redis
brew services start redis
```

**Windows：**
建議使用 Docker 或 WSL2

### 驗證安裝

```bash
# 測試連接
redis-cli ping
# 應該返回：PONG

# 簡單測試
redis-cli
> SET test "hello"
> GET test
> exit
```

## 雲端 Redis（正式環境）

上架 App Store 時，建議使用雲端 Redis 服務：

### 1. **Upstash**（推薦，免費額度高）
- 網站：https://upstash.com/
- 免費額度：10,000 requests/天
- 設定簡單，支援全球節點

```bash
# 註冊後取得連線資訊
REDIS_HOST=your-redis.upstash.io
REDIS_PORT=6379
REDIS_PASSWORD=your-password
```

### 2. **Redis Cloud**（Redis 官方）
- 網站：https://redis.com/cloud/
- 免費額度：30MB 記憶體

### 3. **AWS ElastiCache** / **GCP Memorystore**
- 適合大型應用
- 需要付費

## 配置專案

### 1. 安裝 Python Redis 套件

```bash
pip install -r requirements.txt
```

### 2. 設定環境變數

編輯 `.env.local`（本地開發）：
```bash
# 如果已安裝 Redis，設為 true
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0
```

編輯 `.env.prod`（正式環境）：
```bash
REDIS_ENABLED=true
REDIS_HOST=your-redis-prod-host.com
REDIS_PORT=6379
REDIS_PASSWORD=your-strong-password
REDIS_DB=0
```

### 3. 測試連接

建立測試檔案並執行：

```python
# test_redis.py
from app.db.redis import get_redis

redis = get_redis()
if redis:
    redis.set("test", "Hello Redis!")
    print(f"✓ Redis 連接成功：{redis.get('test')}")
else:
    print("Redis 未啟用")
```

```bash
ENV=local python3 -c "from app.db.redis import get_redis; r=get_redis(); print('✓ Redis OK' if r and r.ping() else 'Redis 未啟用')"
```

## Redis 使用範例

### 1. 驗證碼存儲

```python
from app.db.redis import get_redis

redis = get_redis()
if redis:
    # 存儲驗證碼（5 分鐘過期）
    redis.setex(f"otp:{phone}", 300, "123456")

    # 取得驗證碼
    code = redis.get(f"otp:{phone}")

    # 刪除驗證碼
    redis.delete(f"otp:{phone}")
```

### 2. API 限流

```python
from app.db.redis import get_redis

redis = get_redis()
if redis:
    key = f"rate_limit:{user_id}"

    # 增加計數
    count = redis.incr(key)

    if count == 1:
        # 第一次請求，設定 1 小時過期
        redis.expire(key, 3600)

    if count > 100:
        raise HTTPException(429, "請求過於頻繁")
```

### 3. 資料快取

```python
from app.db.redis import get_redis
import json

redis = get_redis()
if redis:
    # 快取資料（1 小時）
    data = {"name": "Trip", "location": "Tokyo"}
    redis.setex("trip:123", 3600, json.dumps(data))

    # 讀取快取
    cached = redis.get("trip:123")
    if cached:
        trip = json.loads(cached)
```

## 常見問題

### Q1: 本地開發一定要裝 Redis 嗎？
**A:** 不用！設定 `REDIS_ENABLED=false` 即可。大部分功能不需要 Redis。

### Q2: Docker Redis 資料會消失嗎？
**A:** 預設會。如果需要持久化：
```bash
docker run -d \
  --name solotrip-redis \
  -p 6379:6379 \
  -v redis-data:/data \
  redis:7-alpine redis-server --appendonly yes
```

### Q3: 正式環境 Redis 要多大？
**A:** 初期 30-100MB 就夠。隨著用戶增長再擴充。

### Q4: Redis 密碼安全嗎？
**A:** 正式環境務必：
- 設定強密碼
- 只允許特定 IP 連接
- 使用 SSL/TLS（雲端服務通常內建）

## 監控 Redis

```bash
# 查看 Redis 資訊
redis-cli info

# 查看所有 keys
redis-cli keys "*"

# 監控即時命令
redis-cli monitor

# 查看記憶體使用
redis-cli info memory
```

## 總結

- **本地開發**：可選，使用 Docker 最方便
- **測試環境**：建議啟用，使用 Upstash 免費版
- **正式環境**：必須啟用，使用雲端 Redis 服務

有問題隨時調整配置！
