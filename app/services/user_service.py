from typing import Optional, Dict, Any
from datetime import datetime
from passlib.context import CryptContext
from app.repositories_DAO.user_repository import UserRepository, get_user_repository
from app.models_Entity.user import User
from app.core.security import create_token, create_refresh_token
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from app.core.config import settings

# 密碼加密設定（使用 bcrypt 算法）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# For lazy migration in the future
# pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated=["bcrypt"])



class UserService:
    """
    User Service - 業務邏輯層
    處理用戶相關的業務邏輯
    """

    def __init__(self, user_repository: Optional[UserRepository] = None):
        """
        構造函數 - 支援依賴注入

        Args:
            user_repository: UserRepository 實例（可選，支援 DI）
                           如果不提供，會自動創建新實例（向後兼容）
        """
        self.user_repository = user_repository or UserRepository()

    def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        建立新用戶

        Args:
            user_data: 用戶資料字典，包含 email, password 等欄位

        Returns:
            Dict[str, Any]: 已創建的用戶資料（不含密碼）

        Raises:
            ValueError: 當 email 已存在或必填欄位缺失時
        """

        # 1. 驗證 email 是否已存在
        if not user_data.get("email"):
            raise ValueError("Email not provided")

        if self.user_repository.exists_by_email(user_data["email"]):
            raise ValueError("Email already exists")

        # 2. 驗證 username 是否已存在
        if user_data.get("username"):
            if self.user_repository.exists_by_username(user_data["username"]):
                raise ValueError("Username already exists")

        # 3. 準備用戶資料
        new_user_data = {
            "email": user_data["email"],
            "username": user_data.get("username", user_data["email"].split("@")[0]),
            "password_hash": pwd_context.hash(user_data["password"]),  # 加密密碼
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name"),
            "phone_number": user_data.get("phone_number"),
            "role_id": user_data.get("role_id", "customer"),  # 預設角色
            "is_suspended": False,
        }

        # 4. 寫入資料庫
        saved_user = self.user_repository.create(new_user_data)

        # 5. 可以在這裡建立關聯資料（例如用戶檔案）
        # profile_id = self._create_profile_for_new_user(saved_user)
        # saved_user = self.user_repository.update(saved_user["id"], {"profile_id": profile_id})

        # 移除密碼 hash 不返回給前端
        saved_user.pop("password_hash", None)

        return saved_user

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根據 email 取得用戶"""
        user = self.user_repository.find_by_email(email)
        if user:
            user.pop("password_hash", None)  # 不返回密碼
        return user

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """根據 ID 取得用戶"""
        user = self.user_repository.find_by_id(user_id)
        if user:
            user.pop("password_hash", None)  # 不返回密碼
        return user

    def update_user(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新用戶資料"""
        # 如果有密碼更新，需要加密
        if "password" in update_data:
            update_data["password_hash"] = pwd_context.hash(update_data.pop("password"))

        updated_user = self.user_repository.update(user_id, update_data)
        if updated_user:
            updated_user.pop("password_hash", None)

        return updated_user

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """驗證密碼（用於登入）"""
        return pwd_context.verify(plain_password, hashed_password)

    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """
        驗證用戶登入憑證

        Args:
            email: 用戶 email
            password: 明文密碼

        Returns:
            Optional[Dict[str, Any]]: 驗證成功返回用戶資料，失敗返回 None
        """
        user = self.user_repository.find_by_email(email)
        if not user:
            return None

        if not self.verify_password(password, user["password_hash"]):
            return None

        # 登入成功，移除密碼返回用戶資料
        user.pop("password_hash", None)
        return user

    def get_all_users(self, page: int = 1, page_size: int = 10) -> list:
        """取得所有用戶（分頁）"""
        users = self.user_repository.find_all(page, page_size)
        # 移除所有密碼
        for user in users:
            user.pop("password_hash", None)
        return users

    def delete_user(self, user_id: str) -> bool:
        """
        刪除用戶

        Args:
            user_id: 用戶 ID

        Returns:
            bool: 是否刪除成功
        """
        return self.user_repository.delete(user_id)

    def register_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        註冊新用戶（與 create_user 相同，但名稱更語義化）
        供路由層調用
        """
        return self.create_user(user_data)

    def login(self, credentials: Dict[str, Any]) -> Optional[str]:
        """
        用戶登入，返回 JWT token

        Args:
            credentials: 包含 email 和 password 的字典

        Returns:
            Optional[str]: 登入成功返回 JWT token，失敗返回 None
        """
        email = credentials.get("email") or credentials.get("email_or_phone")
        password = credentials.get("password")

        if not email or not password:
            return None

        # 驗證用戶
        user = self.authenticate_user(email, password)
        if not user:
            return None

        # 生成 JWT token
        access_token = create_token(
            sub=user.get("id"),
            role=user.get("role_id", "customer")
        )

        return {"access_token": access_token,
                "refresh_token": create_refresh_token(sub=user["id"]),
                "token_type": "bearer",
        }

    def oauth_login(
        self,
        provider: str,
        id_token: str,
    ) -> dict:
        
        if provider == "google":
            try:
                id_info = google_id_token.verify_oauth2_token(
                    id_token,
                    google_requests.Request(),
                    settings.GOOGLE_CLIENT_ID,
                )
            except ValueError:
                raise ValueError("Invalid Google token")
            
            email = id_info["email"]
            provider_user_id = id_info["sub"]
            name = id_info.get("name", "")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        
        # Look up if this user exist or not by searching the email
        user = self.user_repository.find_by_email(email)

        if not user:
            # Create a new user, without password
            user = self.user_repository.create({
                "email": email,
                "first_name": name,                                                                                                                                                  
                "username": email.split("@")[0],                                                                                   
                "password_hash": "",                                                                                                                                                 
                "provider": provider,                                                                                                                                                
                "provider_user_id": provider_user_id,                                          
            })
        
        access_token = create_token(sub=user["id"])
        refresh_token = create_refresh_token(sub=user["id"])
        return {"access_token": access_token, "refresh_token": refresh_token}  

# ============================================================================
# 依賴注入函數 (Dependency Injection Functions)
# ============================================================================

def get_user_service() -> UserService:
    """
    依賴注入函數 - 提供 UserService 實例

    實現完整的依賴鏈：
    Database (Supabase) → Repository → Service

    FastAPI 會在需要時自動調用此函數來注入依賴

    Returns:
        UserService: 配置好依賴的 UserService 實例
    """
    repository = get_user_repository()  # 注入 Repository
    return UserService(user_repository=repository)
