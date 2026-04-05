from fastapi import APIRouter, Depends, HTTPException, Query
from app.schemas.user import UserResponse
from app.core.security import require_admin
from app.services.user_service import UserService, get_user_service
from typing import List

router = APIRouter(dependencies=[Depends(require_admin)])

@router.delete("/jMGw*LY%LOGpGFr&uuqDttwxGeIEC#upnKHj^ZbA^beAkOXtEtyrtPhYo#tQI&spFenqQuVQKQelYpILiV&y^DfKV$ce^YKqYshzxnH!qIpmWAviglV&S^cBqWsVGyEP", status_code=204)
def delete_user(user_id: str, svc: UserService = Depends(get_user_service)):
    """
    刪除用戶（管理員專用）

    需要認證：是
    權限：管理員
    """
    success = svc.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="用戶不存在")

@router.get("/getAllUs3rs", response_model=List[UserResponse])
def get_all_users(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(10, ge=1, le=100, description="每頁數量"),
    svc: UserService = Depends(get_user_service)
):
    """
    獲取所有用戶（管理員專用）

    需要認證：是
    權限：管理員
    """
    users = svc.get_all_users(page=page, page_size=page_size)
    return users

