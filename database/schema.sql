-- ============================================================================
-- Solotrip 資料庫架構 - Phase 1
-- ============================================================================
-- 說明：在 Supabase Dashboard 中執行此 SQL
-- 路徑：Database -> SQL Editor -> New Query -> 貼上並執行
-- ============================================================================

-- 啟用 UUID 擴展（如果尚未啟用）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. Users 表（應該已經存在，這裡僅供參考）
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone_number VARCHAR(20),
    profile_id UUID,
    role_id VARCHAR(50) DEFAULT 'customer',
    is_suspended BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 為 users 表創建索引（優化查詢效能）
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- ============================================================================
-- 2. Trips 表（旅程主表）- Phase 1 核心
-- ============================================================================
CREATE TABLE IF NOT EXISTS trips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'planning',
    -- status 可能的值: 'planning', 'ongoing', 'completed', 'cancelled'
    is_public BOOLEAN DEFAULT FALSE,
    cover_image_url TEXT,
    budget_amount DECIMAL(10, 2),
    budget_currency VARCHAR(3) DEFAULT 'USD',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 約束：結束日期必須晚於開始日期
    CONSTRAINT check_dates CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date)
);

-- 為 trips 表創建索引
CREATE INDEX IF NOT EXISTS idx_trips_owner_id ON trips(owner_id);
CREATE INDEX IF NOT EXISTS idx_trips_status ON trips(status);
CREATE INDEX IF NOT EXISTS idx_trips_start_date ON trips(start_date);
CREATE INDEX IF NOT EXISTS idx_trips_created_at ON trips(created_at DESC);

-- ============================================================================
-- 3. Trip Destinations 表（旅程目的地）- Phase 1
-- ============================================================================
CREATE TABLE IF NOT EXISTS trip_destinations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trip_id UUID NOT NULL REFERENCES trips(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    address TEXT,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    place_id VARCHAR(255),  -- Google Places API ID（Phase 3 會用到）
    visit_date DATE,
    visit_start_time TIME,
    visit_end_time TIME,
    order_index INTEGER NOT NULL DEFAULT 0,  -- 訪問順序
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- 確保同一個 trip 內的 order_index 唯一
    CONSTRAINT unique_trip_order UNIQUE (trip_id, order_index)
);

-- 為 trip_destinations 表創建索引
CREATE INDEX IF NOT EXISTS idx_destinations_trip_id ON trip_destinations(trip_id);
CREATE INDEX IF NOT EXISTS idx_destinations_order ON trip_destinations(trip_id, order_index);

-- ============================================================================
-- 4. 自動更新 updated_at 的觸發器函數
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 為 trips 表添加觸發器
DROP TRIGGER IF EXISTS update_trips_updated_at ON trips;
CREATE TRIGGER update_trips_updated_at
    BEFORE UPDATE ON trips
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 為 trip_destinations 表添加觸發器
DROP TRIGGER IF EXISTS update_trip_destinations_updated_at ON trip_destinations;
CREATE TRIGGER update_trip_destinations_updated_at
    BEFORE UPDATE ON trip_destinations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 為 users 表添加觸發器（如果尚未添加）
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 5. Row Level Security (RLS) - 可選，但推薦
-- ============================================================================
-- 啟用 RLS
ALTER TABLE trips ENABLE ROW LEVEL SECURITY;
ALTER TABLE trip_destinations ENABLE ROW LEVEL SECURITY;

-- Trips 表的安全策略：用戶只能訪問自己的旅程或公開的旅程
CREATE POLICY "Users can view their own trips" ON trips
    FOR SELECT
    USING (owner_id = auth.uid() OR is_public = TRUE);

CREATE POLICY "Users can insert their own trips" ON trips
    FOR INSERT
    WITH CHECK (owner_id = auth.uid());

CREATE POLICY "Users can update their own trips" ON trips
    FOR UPDATE
    USING (owner_id = auth.uid());

CREATE POLICY "Users can delete their own trips" ON trips
    FOR DELETE
    USING (owner_id = auth.uid());

-- Trip Destinations 表的安全策略：只有旅程擁有者可以管理目的地
CREATE POLICY "Users can view destinations of their trips" ON trip_destinations
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM trips
        WHERE trips.id = trip_destinations.trip_id
        AND (trips.owner_id = auth.uid() OR trips.is_public = TRUE)
    ));

CREATE POLICY "Users can insert destinations to their trips" ON trip_destinations
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM trips
        WHERE trips.id = trip_destinations.trip_id
        AND trips.owner_id = auth.uid()
    ));

CREATE POLICY "Users can update destinations of their trips" ON trip_destinations
    FOR UPDATE
    USING (EXISTS (
        SELECT 1 FROM trips
        WHERE trips.id = trip_destinations.trip_id
        AND trips.owner_id = auth.uid()
    ));

CREATE POLICY "Users can delete destinations of their trips" ON trip_destinations
    FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM trips
        WHERE trips.id = trip_destinations.trip_id
        AND trips.owner_id = auth.uid()
    ));

-- ============================================================================
-- 6. 測試資料（可選）
-- ============================================================================
-- 注意：實際部署時應該刪除或註解掉這部分

-- 假設有一個測試用戶（替換為實際的用戶 ID）
-- INSERT INTO trips (title, description, start_date, end_date, owner_id, status)
-- VALUES
--     ('東京7日遊', '櫻花季的東京之旅', '2024-04-01', '2024-04-07', 'YOUR_USER_ID_HERE', 'planning'),
--     ('台北週末遊', '美食之旅', '2024-05-15', '2024-05-17', 'YOUR_USER_ID_HERE', 'planning');

-- ============================================================================
-- 執行完成後，檢查表是否創建成功：
-- ============================================================================
-- SELECT * FROM trips;
-- SELECT * FROM trip_destinations;
-- ============================================================================
