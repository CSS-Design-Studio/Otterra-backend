from datetime import date, datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl
from decimal import Decimal
from enum import Enum


# ============================================================================
# Trip Destination Schemas
# ============================================================================
class TripStatus(str, Enum):
    planning = "planning"
    ongoing = "ongoing"
    completed = "completed"
    cancelled = "cancelled"

# ============================================================================
# Trip Destination Schemas
# ============================================================================

class TripDestinationBase(BaseModel):
    """目的地基礎 Schema"""
    name: str = Field(..., min_length=1, max_length=255, description="目的地名稱")
    description: Optional[str] = Field(None, max_length = 2000, description="目的地描述")
    address: Optional[str] = Field(None, description="地址")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="緯度")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="經度")
    place_id: Optional[str] = Field(None, description="Google Places ID")
    visit_date: Optional[date] = Field(None, description="訪問日期")
    visit_start_time: Optional[time] = Field(None, description="訪問開始時間")
    visit_end_time: Optional[time] = Field(None, description="訪問結束時間")
    order_index: int = Field(default=0, ge=0, description="訪問順序")
    notes: Optional[str] = Field(None, max_length = 2000, description="備註")


class TripDestinationCreate(TripDestinationBase):
    """創建目的地的請求 Schema"""
    pass


class TripDestinationUpdate(BaseModel):
    """更新目的地的請求 Schema（所有欄位可選）"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    place_id: Optional[str] = None
    visit_date: Optional[date] = None
    visit_start_time: Optional[time] = None
    visit_end_time: Optional[time] = None
    order_index: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class TripDestinationResponse(TripDestinationBase):
    """目的地響應 Schema"""
    id: str
    trip_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Trip Schemas
# ============================================================================

class TripBase(BaseModel):
    """旅程基礎 Schema"""
    title: str = Field(..., min_length=1, max_length=255, description="旅程標題")
    description: Optional[str] = Field(None, description="旅程描述")
    start_date: Optional[date] = Field(None, description="開始日期")
    end_date: Optional[date] = Field(None, description="結束日期")
    status: Optional[TripStatus] = Field(default=TripStatus.planning, description="status")
    is_public: Optional[bool] = Field(default=False, description="是否公開")
    cover_image_url: Optional[HttpUrl] = Field(None, description="封面圖片 URL")
    budget_amount: Optional[float] = Field(None, ge=0, description="預算金額")
    budget_currency: Optional[str] = Field(default='USD', description="預算幣別")


class TripCreate(TripBase):
    """
    創建旅程的請求 Schema

    注意：owner_id 會從 JWT token 中自動獲取，不需要前端傳遞
    """
    destinations: Optional[List[TripDestinationCreate]] = Field(
        default=None,
        description="目的地列表（可選）"
    )


class TripUpdate(BaseModel):
    """
    更新旅程的請求 Schema（所有欄位可選）
    """
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None
    cover_image_url: Optional[str] = None
    budget_amount: Optional[float] = Field(None, ge=0)
    budget_currency: Optional[str] = None


class TripResponse(TripBase):
    """
    旅程響應 Schema
    返回給前端的完整資料
    """
    id: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    destinations: Optional[List[TripDestinationResponse]] = Field(
        default=None,
        description="目的地列表"
    )

    class Config:
        from_attributes = True


class TripListResponse(BaseModel):
    """
    旅程列表響應 Schema
    用於分頁查詢
    """
    total: int = Field(..., description="總數量")
    page: int = Field(..., description="當前頁碼")
    page_size: int = Field(..., description="每頁數量")
    trips: List[TripResponse] = Field(..., description="旅程列表")


class TripStatusUpdate(BaseModel):
    """
    更新旅程狀態的請求 Schema
    """
    status: TripStatus = Field(..., description="planning/ongoing/completed/cancelled")
