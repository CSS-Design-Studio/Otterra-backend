from fastapi import APIRouter, Depends, HTTPException
from app.schemas_DTO.auth import LoginRequest, TokenResponse, OAuthCallBackRequest
from app.services.user_service import UserService, get_user_service
from app.schemas_DTO.user import UserCreate, UserUpdate, UserResponse, UserProfileResponse
from app.core.security import get_current_token, get_optional_token
from app.core.rate_limit import rate_limit_login, rate_limit_register


router = APIRouter()

@router.post("/save", response_model=UserResponse)
def register_user(payload: UserCreate, svc: UserService = Depends(get_user_service), _: None = Depends(rate_limit_register)):
    """
    用戶註冊端點
    創建新用戶帳號
    """
    user = svc.register_user(payload.model_dump())
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, svc: UserService = Depends(get_user_service), _: None = Depends(rate_limit_login)):
    """
    用戶登入端點
    驗證憑證並返回 JWT token
    """
    token = svc.login(payload.model_dump())
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(**token)

@router.post("/oauth-callback", response_model=TokenResponse)
def oauth_callback(
    payload: OAuthCallBackRequest,
    svc: UserService = Depends(get_user_service),
):
    try:
        token = svc.oauth_login(payload.provider, payload.id_token)
        return TokenResponse(**token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@router.post("/logout", response_model=TokenResponse)




@router.get("/me", response_model=UserProfileResponse)
def get_profile(svc : UserService = Depends(get_user_service),
                      current_user: dict = Depends(get_current_token)
                ):

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unthorised/ Invalid token")
                
                

    user = svc.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
               
               
    return user

@router.put("/me", response_model=UserProfileResponse)
def update_profile(
    payload: UserUpdate,
    svc: UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_token)
):
    """
    更新用戶個人資料
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unthorised/ Invalid token")
    update_data = payload.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    

    updated_user = svc.update_user(user_id, update_data)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user

@router.delete("/me", status_code=200)
def delete_user(
    svc : UserService = Depends(get_user_service),
    current_user: dict = Depends(get_current_token)
):
    """
    刪除用戶個人帳號
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unthorised/ Invalid token")
        
    success = svc.delete_user(user_id)

    if not success:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"message": "User deleted successfully"}

@router.post("/refresh", response_model=TokenResponse)
def refresh_token(payload:dict = Depends(get_current_token)):
    """
    Refresh users' token when it expired
    """
    if payload.get("type") != "refresh":
        raise HTTPException(status_code = 401, detail = "Invalid token type")
    
    return{
        "access_token": create_token(sub=payload["sub"]),
        "refresh_token": create_refresh_token(sub=payload["sub"]),
    }