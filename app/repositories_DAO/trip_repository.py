from typing import Optional, List, Dict, Any
from datetime import datetime
from app.db.supabase import get_supabase


class TripRepository:
    """
    Trip Repository - 資料存取層
    負責旅程數據的 CRUD 操作
    """

    def __init__(self):
        self.supabase = get_supabase()
        self.table_name = "trips"
        self.destinations_table = "trip_destinations"

    # ========================================================================
    # Trip CRUD 操作
    # ========================================================================

    def create(self, trip_data: dict) -> dict:
        """
        創建新旅程

        Args:
            trip_data: 旅程資料字典

        Returns:
            dict: 已創建的旅程資料
        """
        # 加入時間戳記
        trip_data["created_at"] = datetime.utcnow().isoformat()
        trip_data["updated_at"] = datetime.utcnow().isoformat()

        response = self.supabase.table(self.table_name)\
            .insert(trip_data)\
            .execute()

        return response.data[0] if response.data else None

    def find_by_id(self, trip_id: str, include_destinations: bool = False) -> Optional[dict]:
        """
        根據 ID 查找旅程

        Args:
            trip_id: 旅程 ID
            include_destinations: 是否包含目的地列表

        Returns:
            Optional[dict]: 旅程資料，不存在則返回 None
        """
        response = self.supabase.table(self.table_name)\
            .select("*")\
            .eq("id", trip_id)\
            .execute()

        if not response.data:
            return None

        trip = response.data[0]

        # 如果需要，加載目的地
        if include_destinations:
            trip["destinations"] = self.get_destinations_by_trip_id(trip_id)

        return trip

    def find_by_owner(
        self,
        owner_id: str,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        include_destinations: bool = False
    ) -> List[dict]:
        """
        查詢用戶的所有旅程（分頁）

        Args:
            owner_id: 用戶 ID
            page: 頁碼（從 1 開始）
            page_size: 每頁數量
            status: 過濾狀態（可選）
            include_destinations: 是否包含目的地列表

        Returns:
            List[dict]: 旅程列表
        """
        offset = (page - 1) * page_size

        query = self.supabase.table(self.table_name)\
            .select("*")\
            .eq("owner_id", owner_id)

        # 如果指定狀態，添加過濾
        if status:
            query = query.eq("status", status)

        response = query\
            .order("created_at", desc=True)\
            .range(offset, offset + page_size - 1)\
            .execute()

        trips = response.data

        # 如果需要，為每個旅程加載目的地
        if include_destinations:
            for trip in trips:
                trip["destinations"] = self.get_destinations_by_trip_id(trip["id"])

        return trips

    def count_by_owner(self, owner_id: str, status: Optional[str] = None) -> int:
        """
        統計用戶的旅程數量

        Args:
            owner_id: 用戶 ID
            status: 過濾狀態（可選）

        Returns:
            int: 旅程數量
        """
        query = self.supabase.table(self.table_name)\
            .select("id", count="exact")\
            .eq("owner_id", owner_id)

        if status:
            query = query.eq("status", status)

        response = query.execute()
        return response.count if hasattr(response, 'count') else len(response.data)

    def update(self, trip_id: str, trip_data: dict) -> Optional[dict]:
        """
        更新旅程資料

        Args:
            trip_id: 旅程 ID
            trip_data: 要更新的資料字典

        Returns:
            Optional[dict]: 更新後的旅程資料
        """
        trip_data["updated_at"] = datetime.utcnow().isoformat()

        response = self.supabase.table(self.table_name)\
            .update(trip_data)\
            .eq("id", trip_id)\
            .execute()

        return response.data[0] if response.data else None

    def delete(self, trip_id: str) -> bool:
        """
        刪除旅程（cascade 會自動刪除關聯的目的地）

        Args:
            trip_id: 旅程 ID

        Returns:
            bool: 是否刪除成功
        """
        response = self.supabase.table(self.table_name)\
            .delete()\
            .eq("id", trip_id)\
            .execute()

        return len(response.data) > 0

    def exists(self, trip_id: str) -> bool:
        """
        檢查旅程是否存在

        Args:
            trip_id: 旅程 ID

        Returns:
            bool: 是否存在
        """
        response = self.supabase.table(self.table_name)\
            .select("id")\
            .eq("id", trip_id)\
            .execute()

        return len(response.data) > 0

    # ========================================================================
    # Trip Destinations CRUD 操作
    # ========================================================================

    def get_destinations_by_trip_id(self, trip_id: str) -> List[dict]:
        """
        獲取旅程的所有目的地（按順序排序）

        Args:
            trip_id: 旅程 ID

        Returns:
            List[dict]: 目的地列表
        """
        response = self.supabase.table(self.destinations_table)\
            .select("*")\
            .eq("trip_id", trip_id)\
            .order("order_index", desc=False)\
            .execute()

        return response.data

    def create_destination(self, destination_data: dict) -> dict:
        """
        創建新目的地

        Args:
            destination_data: 目的地資料字典

        Returns:
            dict: 已創建的目的地資料
        """
        destination_data["created_at"] = datetime.utcnow().isoformat()
        destination_data["updated_at"] = datetime.utcnow().isoformat()

        response = self.supabase.table(self.destinations_table)\
            .insert(destination_data)\
            .execute()

        return response.data[0] if response.data else None

    def update_destination(self, destination_id: str, destination_data: dict) -> Optional[dict]:
        """
        更新目的地資料

        Args:
            destination_id: 目的地 ID
            destination_data: 要更新的資料字典

        Returns:
            Optional[dict]: 更新後的目的地資料
        """
        destination_data["updated_at"] = datetime.utcnow().isoformat()

        response = self.supabase.table(self.destinations_table)\
            .update(destination_data)\
            .eq("id", destination_id)\
            .execute()

        return response.data[0] if response.data else None

    def delete_destination(self, destination_id: str) -> bool:
        """
        刪除目的地

        Args:
            destination_id: 目的地 ID

        Returns:
            bool: 是否刪除成功
        """
        response = self.supabase.table(self.destinations_table)\
            .delete()\
            .eq("id", destination_id)\
            .execute()

        return len(response.data) > 0

    def find_destination_by_id(self, destination_id: str) -> Optional[dict]:
        """
        根據 ID 查找目的地

        Args:
            destination_id: 目的地 ID

        Returns:
            Optional[dict]: 目的地資料
        """
        response = self.supabase.table(self.destinations_table)\
            .select("*")\
            .eq("id", destination_id)\
            .execute()

        return response.data[0] if response.data else None

    def find_public_trips(self, page: int = 1, page_size: int = 10, keyword: Optional[str] = None) -> List[dict]:
        """
        查詢公開的旅程
        """
        offset = (page - 1) * page_size
        query = self.supabase.table(self.table_name)\
            .select("*")\
            .eq("is_public", True)\
            .eq("status", "completed")
        
        if keyword:
            query = query.ilike("title", f"%{keyword}%")

        response = query\
            .order("created_at", desc=True)\
            .range(offset, offset + page_size - 1)\
            .execute()

        return response.data




    def count_public_trips(self, keyword: Optional[str] = None) -> int:
        query = self.supabase.table(self.table_name)\
            .select("id", count="exact")\
            .eq("is_public", True)\
            .eq("status", "completed")

        if keyword:
            query = query.ilike("title", f"%{keyword}%")

        response = query.execute()
        return response.count if hasattr(response, "count") else len(response.data)

# ============================================================================
# 依賴注入函數 (Dependency Injection Functions)
# ============================================================================

def get_trip_repository() -> TripRepository:
    """
    依賴注入函數 - 提供 TripRepository 實例

    Repository 會自動獲取 Supabase 客戶端（通過 get_supabase() 的單例模式）

    Returns:
        TripRepository: TripRepository 實例
    """
    return TripRepository()
