# 使用範例 - 參考 Kulaa 架構

本專案參考 Kulaa (Java + MongoDB) 的三層架構，使用 FastAPI + Supabase 實現。

## 📐 架構對比

| 層級 | Kulaa (Java) | Solotrip (Python) | 說明 |
|------|-------------|------------------|------|
| **Entity** | `@Document Users.java` | `models/user.py` | 資料模型定義 |
| **Repository** | `UsersRepository.java` | `repositories/user_repository.py` | 資料存取層 |
| **Service** | `UsersServiceImpl.java` | `services/user_service.py` | 業務邏輯層 |

## 📝 建立 User 範例

### Kulaa 的做法 (Java + MongoDB)

```java
// 1. 建立 User 物件
Users users = new Users();
users.setEmail("test@example.com");
users.setPasswordHash(passwordEncoder.encode("password123"));
users.setUsername("testuser");
users.setFirstName("John");
users.setLastName("Doe");
users.setCreatedAt(new Date());

// 2. 寫入 MongoDB
Users savedUser = usersRepository.insert(users);

// 3. 建立關聯資料
savedUser.setProfileId(createProfileForNewUser(savedUser));
usersRepository.save(savedUser);
```

### Solotrip 的等價做法 (Python + Supabase)

```python
# 1. 準備用戶資料
user_data = {
    "email": "test@example.com",
    "password": "password123",
    "username": "testuser",
    "first_name": "John",
    "last_name": "Doe"
}

# 2. 呼叫 Service 建立用戶（會自動加密密碼、加入時間戳記）
user_service = UserService()
saved_user = user_service.create_user(user_data)

# 3. 結果
print(saved_user)
# {
#   "id": "uuid-xxx",
#   "email": "test@example.com",
#   "username": "testuser",
#   "first_name": "John",
#   "last_name": "Doe",
#   "created_at": "2024-01-03T10:00:00",
#   "is_suspended": False
# }
```

## 🔍 查詢 User 範例

### Kulaa (Java)

```java
// 根據 email 查詢
Optional<Users> userOptional = usersRepository.findByEmail("test@example.com");

// 檢查是否存在
boolean exists = usersRepository.existsByEmail("test@example.com");
```

### Solotrip (Python)

```python
# 根據 email 查詢
user = user_service.get_user_by_email("test@example.com")

# 透過 Repository 檢查是否存在
user_repo = UserRepository()
exists = user_repo.exists_by_email("test@example.com")
```

## 🔐 用戶登入驗證

### Kulaa (Java)

```java
// 驗證用戶
Authentication authentication = authenticationManager.authenticate(
    new UsernamePasswordAuthenticationToken(email, password)
);
```

### Solotrip (Python)

```python
# 驗證用戶
user = user_service.authenticate_user(
    email="test@example.com",
    password="password123"
)

if user:
    # 登入成功，user 包含用戶資料（不含密碼）
    print(f"Welcome {user['username']}!")
else:
    # 登入失敗
    print("Invalid credentials")
```

## 📊 在 Supabase 建立資料表

在 Supabase Dashboard 執行以下 SQL 來建立 users 資料表：

```sql
-- 建立 users 資料表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    phone_number TEXT,
    profile_id UUID,
    role_id TEXT DEFAULT 'customer',
    is_suspended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 建立索引提升查詢效能
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- 建立 updated_at 自動更新的觸發器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

## 🧪 完整測試範例

建立檔案 `test_user_creation.py`：

```python
#!/usr/bin/env python3
from app.services.user_service import UserService

def test_create_and_query_user():
    """測試建立和查詢用戶（類似 Kulaa 的做法）"""

    service = UserService()

    # 1. 建立用戶
    print("=== 建立新用戶 ===")
    try:
        user_data = {
            "email": "john.doe@example.com",
            "password": "SecurePass123!",
            "username": "johndoe",
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "+886912345678"
        }

        new_user = service.create_user(user_data)
        print(f"✓ 用戶建立成功: {new_user['email']}")
        print(f"  ID: {new_user['id']}")
        print(f"  用戶名: {new_user['username']}")

    except ValueError as e:
        print(f"✗ 建立失敗: {e}")
        return

    # 2. 查詢用戶
    print("\n=== 查詢用戶 ===")
    found_user = service.get_user_by_email("john.doe@example.com")
    if found_user:
        print(f"✓ 找到用戶: {found_user['username']}")
    else:
        print("✗ 找不到用戶")

    # 3. 驗證登入
    print("\n=== 驗證登入 ===")
    auth_user = service.authenticate_user(
        email="john.doe@example.com",
        password="SecurePass123!"
    )

    if auth_user:
        print(f"✓ 登入成功: {auth_user['username']}")
    else:
        print("✗ 登入失敗")

    # 4. 錯誤密碼測試
    print("\n=== 錯誤密碼測試 ===")
    failed_auth = service.authenticate_user(
        email="john.doe@example.com",
        password="WrongPassword"
    )

    if not failed_auth:
        print("✓ 正確拒絕錯誤密碼")

if __name__ == "__main__":
    test_create_and_query_user()
```

執行：
```bash
python3 test_user_creation.py
```

## 📌 重點總結

### Kulaa 的方式
1. **Entity** 定義資料結構（`@Document`）
2. **Repository** 繼承 `MongoRepository`，自動實作 CRUD
3. **Service** 建立物件、設定屬性、呼叫 `repository.save()`

### Solotrip 的等價實作
1. **Model** 定義資料結構（Pydantic `BaseModel`）
2. **Repository** 封裝 Supabase 操作（`insert`, `select`, `update`）
3. **Service** 準備資料字典、呼叫 `repository.create()`

兩者架構邏輯一致，只是技術棧不同！
