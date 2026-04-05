from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class User(BaseModel):
    """
    User 模型 - 對應 Supabase 的 users 資料表
    定義用戶的數據結構
    """
    id: Optional[str] = None
    email: EmailStr
    username: str
    password_hash: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = None
    profile_id: Optional[str] = None
    role_id: Optional[str] = None
    is_suspended: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # 允許從 ORM 物件轉換
