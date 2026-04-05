from datetime import date, datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field
from decimal import Decimal


class TripDestination(BaseModel):
    """
    旅程目的地模型 - 對應 Supabase 的 trip_destinations 資料表
    每個旅程可以有多個目的地
    """
    id: Optional[str] = None
    trip_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    place_id: Optional[str] = None  # Google Places API ID（Phase 3）
    visit_date: Optional[date] = None
    visit_start_time: Optional[time] = None
    visit_end_time: Optional[time] = None
    order_index: int = 0  # 訪問順序
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v else None,
            time: lambda v: v.isoformat() if v else None,
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None,
        }


class Trip(BaseModel):
    """
    旅程模型 - 對應 Supabase 的 trips 資料表
    Phase 1 的核心業務實體
    """
    id: Optional[str] = None
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    owner_id: str  # 旅程擁有者（user_id）
    status: str = Field(default='planning')  # planning, ongoing, completed, cancelled
    is_public: bool = False  # 是否公開
    cover_image_url: Optional[str] = None
    budget_amount: Optional[Decimal] = None
    budget_currency: str = 'USD'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # 關聯資料（可選，用於返回完整資料）
    destinations: Optional[List[TripDestination]] = None

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: lambda v: float(v) if v else None,
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None,
        }
