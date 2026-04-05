from typing import Optional, List, Dict, Any
from datetime import datetime
from app.repositories_DAO.trip_repository import TripRepository, get_trip_repository
import json
from app.db.redis import get_redis


class TripService:
    """
    Trip Service - 業務邏輯層
    處理旅程相關的業務邏輯
    """

    def __init__(self, trip_repository: Optional[TripRepository] = None):
        """
        構造函數 - 支援依賴注入

        Args:
            trip_repository: TripRepository 實例（可選，支援 DI）
                           如果不提供，會自動創建新實例（向後兼容）
        """
        self.trip_repository = trip_repository or TripRepository()

    # ========================================================================
    # Trip CRUD 操作
    # ========================================================================

    def create_trip(self, trip_data: Dict[str, Any], owner_id: str) -> Dict[str, Any]:
        """
        創建新旅程

        Args:
            trip_data: 旅程資料字典
            owner_id: 旅程擁有者 ID（從 JWT token 獲取）

        Returns:
            Dict[str, Any]: 已創建的旅程資料

        Raises:
            ValueError: 當必填欄位缺失或資料無效時
        """
        # 1. 驗證必填欄位
        if not trip_data.get("title"):
            raise ValueError("旅程標題不能為空")

        # 2. 驗證日期邏輯
        start_date = trip_data.get("start_date")
        end_date = trip_data.get("end_date")
        if start_date and end_date:
            if end_date < start_date:
                raise ValueError("結束日期不能早於開始日期")

        # 3. 設置擁有者
        trip_data["owner_id"] = owner_id

        # 4. 設置預設值
        if "status" not in trip_data:
            trip_data["status"] = "planning"
        if "is_public" not in trip_data:
            trip_data["is_public"] = False

        # 5. 提取目的地資料（如果有）
        destinations_data = trip_data.pop("destinations", None)

        # 6. 創建旅程
        trip = self.trip_repository.create(trip_data)

        # 7. 如果有目的地，創建目的地
        if destinations_data and trip:
            destinations = []
            for idx, dest_data in enumerate(destinations_data):
                dest_data["trip_id"] = trip["id"]
                dest_data["order_index"] = idx
                destination = self.trip_repository.create_destination(dest_data)
                destinations.append(destination)
            trip["destinations"] = destinations

        return trip

    def get_trip_by_id(
        self,
        trip_id: str,
        user_id: str,
        include_destinations: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        根據 ID 獲取旅程

        Args:
            trip_id: 旅程 ID
            user_id: 當前用戶 ID（用於權限檢查）
            include_destinations: 是否包含目的地列表

        Returns:
            Optional[Dict[str, Any]]: 旅程資料，不存在或無權限則返回 None
        """
        trip = self.trip_repository.find_by_id(trip_id, include_destinations)

        if not trip:
            return None

        # 權限檢查：只有擁有者或公開的旅程可以訪問
        if trip["owner_id"] != user_id and not trip.get("is_public", False):
            return None

        return trip

    def get_my_trips(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        include_destinations: bool = False
    ) -> Dict[str, Any]:
        """
        獲取我的旅程列表（分頁）

        Args:
            user_id: 用戶 ID
            page: 頁碼（從 1 開始）
            page_size: 每頁數量
            status: 過濾狀態（可選）
            include_destinations: 是否包含目的地列表

        Returns:
            Dict[str, Any]: 包含 total, page, page_size, trips 的字典
        """
        # 獲取旅程列表
        trips = self.trip_repository.find_by_owner(
            owner_id=user_id,
            page=page,
            page_size=page_size,
            status=status,
            include_destinations=include_destinations
        )

        # 獲取總數
        total = self.trip_repository.count_by_owner(owner_id=user_id, status=status)

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "trips": trips
        }

    def update_trip(
        self,
        trip_id: str,
        trip_data: Dict[str, Any],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        更新旅程

        Args:
            trip_id: 旅程 ID
            trip_data: 要更新的資料
            user_id: 當前用戶 ID（用於權限檢查）

        Returns:
            Optional[Dict[str, Any]]: 更新後的旅程資料

        Raises:
            ValueError: 當資料無效時
            PermissionError: 當無權限時
        """
        # 1. 檢查旅程是否存在
        existing_trip = self.trip_repository.find_by_id(trip_id)
        if not existing_trip:
            return None

        # 2. 權限檢查：只有擁有者可以編輯
        if existing_trip["owner_id"] != user_id:
            raise PermissionError("您沒有權限編輯此旅程")

        # 3. 驗證日期邏輯（如果更新了日期）
        start_date = trip_data.get("start_date") or existing_trip.get("start_date")
        end_date = trip_data.get("end_date") or existing_trip.get("end_date")
        if start_date and end_date:
            # 如果是字符串，轉換為可比較的格式
            if isinstance(start_date, str) and isinstance(end_date, str):
                if end_date < start_date:
                    raise ValueError("結束日期不能早於開始日期")

        # 4. 更新旅程
        updated_trip = self.trip_repository.update(trip_id, trip_data)

        # 5. 加載目的地
        if updated_trip:
            updated_trip["destinations"] = self.trip_repository.get_destinations_by_trip_id(trip_id)

        return updated_trip
    
    def update_trip_status(self, trip_id: str, status: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        更新旅程狀態
        """
        # 1. 檢查旅程是否存在
        validate_statuses = ["planning", "ongoing", "completed", "cancelled"]
        if status not in validate_statuses:
            raise ValueError("Invalid status, must be one of: planning, ongoing, completed, cancelled")

        # 2. 權限檢查：只有擁有者可以更新狀態
        existing_trip = self.trip_repository.find_by_id(trip_id)
        if not existing_trip:
            return None
        return self.trip_repository.update_status(trip_id, {"status": status}, user_id)

            

    def delete_trip(self, trip_id: str, user_id: str) -> bool:
        """
        刪除旅程

        Args:
            trip_id: 旅程 ID
            user_id: 當前用戶 ID（用於權限檢查）

        Returns:
            bool: 是否刪除成功

        Raises:
            PermissionError: 當無權限時
        """
        # 1. 檢查旅程是否存在
        existing_trip = self.trip_repository.find_by_id(trip_id)
        if not existing_trip:
            return False

        # 2. 權限檢查：只有擁有者可以刪除
        if existing_trip["owner_id"] != user_id:
            raise PermissionError("您沒有權限刪除此旅程")

        # 3. 刪除旅程（cascade 會自動刪除目的地）
        return self.trip_repository.delete(trip_id)

    # ========================================================================
    # Trip Destinations 操作
    # ========================================================================

    def add_destination(
        self,
        trip_id: str,
        destination_data: Dict[str, Any],
        user_id: str
    ) -> Dict[str, Any]:
        """
        為旅程添加目的地

        Args:
            trip_id: 旅程 ID
            destination_data: 目的地資料
            user_id: 當前用戶 ID（用於權限檢查）

        Returns:
            Dict[str, Any]: 已創建的目的地資料

        Raises:
            ValueError: 當旅程不存在時
            PermissionError: 當無權限時
        """
        # 1. 檢查旅程是否存在
        trip = self.trip_repository.find_by_id(trip_id)
        if not trip:
            raise ValueError("旅程不存在")

        # 2. 權限檢查：只有擁有者可以添加目的地
        if trip["owner_id"] != user_id:
            raise PermissionError("您沒有權限修改此旅程")

        # 3. 設置 trip_id
        destination_data["trip_id"] = trip_id

        # 4. 如果沒有指定順序，設置為最後
        if "order_index" not in destination_data:
            existing_destinations = self.trip_repository.get_destinations_by_trip_id(trip_id)
            destination_data["order_index"] = len(existing_destinations)

        # 5. 創建目的地
        return self.trip_repository.create_destination(destination_data)

    def update_destination(
        self,
        destination_id: str,
        destination_data: Dict[str, Any],
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        更新目的地

        Args:
            destination_id: 目的地 ID
            destination_data: 要更新的資料
            user_id: 當前用戶 ID（用於權限檢查）

        Returns:
            Optional[Dict[str, Any]]: 更新後的目的地資料

        Raises:
            PermissionError: 當無權限時
        """
        # 1. 檢查目的地是否存在
        destination = self.trip_repository.find_destination_by_id(destination_id)
        if not destination:
            return None

        # 2. 檢查對應的旅程權限
        trip = self.trip_repository.find_by_id(destination["trip_id"])
        if not trip or trip["owner_id"] != user_id:
            raise PermissionError("您沒有權限修改此目的地")

        # 3. 更新目的地
        return self.trip_repository.update_destination(destination_id, destination_data)

    def delete_destination(self, destination_id: str, user_id: str) -> bool:
        """
        刪除目的地

        Args:
            destination_id: 目的地 ID
            user_id: 當前用戶 ID（用於權限檢查）

        Returns:
            bool: 是否刪除成功

        Raises:
            PermissionError: 當無權限時
        """
        # 1. 檢查目的地是否存在
        destination = self.trip_repository.find_destination_by_id(destination_id)
        if not destination:
            return False

        # 2. 檢查對應的旅程權限
        trip = self.trip_repository.find_by_id(destination["trip_id"])
        if not trip or trip["owner_id"] != user_id:
            raise PermissionError("您沒有權限刪除此目的地")

        # 3. 刪除目的地
        return self.trip_repository.delete_destination(destination_id)


    def get_public_trips(
        self,
        page: int = 1,
        page_size: int = 10,
        keyword: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        獲取公開的旅程列表（分頁）
        """
        trips = self.trip_repository.find_public_trips(page, page_size, keyword)
        total = self.trip_repository.count_public_trips(keyword)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "trips": trips
        }

    def save_ai_destinations_to_trip(
        self,
        user_id: str,
        trip_id: str,
        draft_id: str,
        selected_indexes: list[int],
    ) -> bool:
        """"
        Read AI-generated destinations from Redis draft and write selected ones to DB
        Deletes the draft from Redis after saving
        """

        redis = get_redis()
        if not redis:
            return False

        raw = redis.get(f"trip_draft:{user_id}:{draft_id}")
        if not raw:
            return False
        
        trip = self.trip_repository.find_by_id(trip_id)
        if not trip or trip["owner_id"] != user_id:
            return False
        
        destinations = json.loads(raw)
        selected_destinations = [
            d for d in destinations
            if isinstance(d, dict) and d.get("order_index") in selected_indexes
        ]

        for new_index, dest in enumerate(selected_destinations):
            destination_payload = {
                "trip_id": trip_id,
                "name": dest["name"],
                "visit_date": dest.get("visit_date"),
                "visit_start_time": dest.get("visit_start_time"),
                "visit_end_time": dest.get("visit_end_time"),
                "order_index": new_index,
            }
            self.trip_repository.create_destination(destination_payload)

        redis.delete(f"trip_draft:{user_id}:{draft_id}")
        return True


# ============================================================================
# 依賴注入函數 (Dependency Injection Functions)
# ============================================================================

def get_trip_service() -> TripService:
    """
    依賴注入函數 - 提供 TripService 實例

    實現完整的依賴鏈：
    Database (Supabase) → Repository → Service

    FastAPI 會在需要時自動調用此函數來注入依賴

    Returns:
        TripService: 配置好依賴的 TripService 實例
    """
    repository = get_trip_repository()  # 注入 Repository
    return TripService(trip_repository=repository)
