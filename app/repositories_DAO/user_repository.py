from typing import Optional, List
from datetime import datetime
from app.db.supabase import get_supabase
from app.models_Entity.user import User

class UserRepository:
    """
    User Repository - 資料存取層
    負責用戶數據的 CRUD 操作
    """

    def __init__(self):
        self.supabase = get_supabase()
        self.table_name = "users"

    def find_by_email(self, email: str) -> Optional[dict]:
        """根據 email 查找用戶"""
        response = self.supabase.table(self.table_name)\
            .select("*")\
            .eq("email", email)\
            .execute()

        return response.data[0] if response.data else None

    def find_by_username(self, username: str) -> Optional[dict]:
        """根據 username 查找用戶"""
        response = self.supabase.table(self.table_name)\
            .select("*")\
            .eq("username", username)\
            .execute()

        return response.data[0] if response.data else None

    def exists_by_email(self, email: str) -> bool:
        """檢查 email 是否已存在"""
        response = self.supabase.table(self.table_name)\
            .select("id")\
            .eq("email", email)\
            .execute()

        return len(response.data) > 0

    def exists_by_username(self, username: str) -> bool:
        """檢查 username 是否已存在"""
        response = self.supabase.table(self.table_name)\
            .select("id")\
            .eq("username", username)\
            .execute()

        return len(response.data) > 0

    def create(self, user_data: dict) -> dict:
        """
        建立新用戶

        Args:
            user_data: 用戶資料字典

        Returns:
            dict: 已創建的用戶資料
        """
        # 加入時間戳記
        user_data["created_at"] = datetime.utcnow().isoformat()
        user_data["updated_at"] = datetime.utcnow().isoformat()

        response = self.supabase.table(self.table_name)\
            .insert(user_data)\
            .execute()

        return response.data[0] if response.data else None

    def update(self, user_id: str, user_data: dict) -> dict:
        """
        更新用戶資料

        Args:
            user_id: 用戶 ID
            user_data: 要更新的用戶資料字典

        Returns:
            dict: 更新後的用戶資料
        """
        user_data["updated_at"] = datetime.utcnow().isoformat()

        response = self.supabase.table(self.table_name)\
            .update(user_data)\
            .eq("id", user_id)\
            .execute()

        return response.data[0] if response.data else None

    def find_by_id(self, user_id: str) -> Optional[dict]:
        """根據 ID 查找用戶"""
        response = self.supabase.table(self.table_name)\
            .select("*")\
            .eq("id", user_id)\
            .execute()

        return response.data[0] if response.data else None

    def find_all(self, page: int = 1, page_size: int = 10) -> List[dict]:
        """查詢所有用戶（分頁）"""
        offset = (page - 1) * page_size

        response = self.supabase.table(self.table_name)\
            .select("*")\
            .order("created_at", desc=True)\
            .range(offset, offset + page_size - 1)\
            .execute()

        return response.data

    def delete(self, user_id: str) -> bool:
        """刪除用戶"""
        response = self.supabase.table(self.table_name)\
            .delete()\
            .eq("id", user_id)\
            .execute()

        return len(response.data) > 0


# ============================================================================
# 依賴注入函數 (Dependency Injection Functions)
# ============================================================================

def get_user_repository() -> UserRepository:
    """
    依賴注入函數 - 提供 UserRepository 實例

    Repository 會自動獲取 Supabase 客戶端（通過 get_supabase() 的單例模式）

    Returns:
        UserRepository: UserRepository 實例
    """
    return UserRepository()
