from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from app.schemas_DTO.ai import SaveAiDraftRequest
from app.schemas_DTO.trip import (
    TripCreate,
    TripUpdate,
    TripResponse,
    TripListResponse,
    TripDestinationCreate,
    TripDestinationUpdate,
    TripDestinationResponse,
    TripStatusUpdate
)
from app.services.trip_service import TripService, get_trip_service
from app.core.security import get_current_token, get_optional_token


router = APIRouter()


# ============================================================================
# Trip CRUD 端點
# ============================================================================

@router.post("", response_model=TripResponse, status_code=201)
def create_trip(
    payload: TripCreate,
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    創建新旅程

    需要認證：是
    權限：所有登入用戶
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="無效的認證 token")

    try:
        trip = svc.create_trip(payload.model_dump(exclude_unset=True), user_id)
        return trip
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=TripListResponse)
def get_my_trips(
    page: int = Query(1, ge=1, description="頁碼"),
    page_size: int = Query(10, ge=1, le=100, description="每頁數量"),
    status: Optional[str] = Query(None, description="過濾狀態"),
    include_destinations: bool = Query(False, description="是否包含目的地列表"),
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    獲取我的旅程列表（分頁）

    需要認證：是
    權限：所有登入用戶

    查詢參數：
    - page: 頁碼（從 1 開始）
    - page_size: 每頁數量（1-100）
    - status: 過濾狀態（planning/ongoing/completed/cancelled）
    - include_destinations: 是否包含目的地列表
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="無效的認證 token")

    result = svc.get_my_trips(
        user_id=user_id,
        page=page,
        page_size=page_size,
        status=status,
        include_destinations=include_destinations
    )
    return result


@router.post("/from-draft", status_code=201)
def save_destination_from_ai(
    body: SaveAiDraftRequest,
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    Save selected AI-generated destinations from Redis draft into a trip
    """
    user_id = current_user.get("sub")
    success = svc.save_ai_destinations_to_trip(
        user_id=user_id,
        trip_id=body.trip_id,
        draft_id=body.draft_id,
        selected_indexes=body.selected_indexes,
    ) 

    if not success:
        raise HTTPException(status_code=404, detail="Draft not found, expired, or no permission")
    return {"message": "Destinations saved"}

    
@router.get("/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: str,
    include_destinations: bool = Query(True, description="是否包含目的地列表"),
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    獲取單個旅程詳情

    需要認證：是
    權限：旅程擁有者或公開旅程
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="無效的認證 token")

    trip = svc.get_trip_by_id(trip_id, user_id, include_destinations)
    if not trip:
        raise HTTPException(status_code=404, detail="旅程不存在或無權訪問")

    return trip


@router.put("/{trip_id}", response_model=TripResponse)
def update_trip(
    trip_id: str,
    payload: TripUpdate,
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    更新旅程資訊

    需要認證：是
    權限：旅程擁有者
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="無效的認證 token")

    try:
        trip = svc.update_trip(trip_id, payload.model_dump(exclude_unset=True), user_id)
        if not trip:
            raise HTTPException(status_code=404, detail="旅程不存在")
        return trip
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/{trip_id}", status_code=204)
def delete_trip(
    trip_id: str,
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    刪除旅程

    需要認證：是
    權限：旅程擁有者
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="無效的認證 token")

    try:
        success = svc.delete_trip(trip_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="旅程不存在")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


# ============================================================================
# Trip Destinations 端點
# ============================================================================

@router.post("/{trip_id}/destinations", response_model=TripDestinationResponse, status_code=201)
def add_destination(
    trip_id: str,
    payload: TripDestinationCreate,
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    為旅程添加目的地

    需要認證：是
    權限：旅程擁有者
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="無效的認證 token")

    try:
        destination = svc.add_destination(trip_id, payload.model_dump(exclude_unset=True), user_id)
        return destination
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/destinations/{destination_id}", response_model=TripDestinationResponse)
def update_destination(
    destination_id: str,
    payload: TripDestinationUpdate,
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    更新目的地資訊

    需要認證：是
    權限：旅程擁有者
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="無效的認證 token")

    try:
        destination = svc.update_destination(destination_id, payload.model_dump(exclude_unset=True), user_id)
        if not destination:
            raise HTTPException(status_code=404, detail="目的地不存在")
        return destination
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/destinations/{destination_id}", status_code=204)
def delete_destination(
    destination_id: str,
    svc: TripService = Depends(get_trip_service),
    current_user: dict = Depends(get_current_token)
):
    """
    刪除目的地

    需要認證：是
    權限：旅程擁有者
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unthorised/ Invalid token")

    try:
        success = svc.delete_destination(destination_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail="Destination not found")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/explore", response_model=TripListResponse)
def get_public_trips(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = Query(None, description="Keyword"),
    svc: TripService = Depends(get_trip_service),
    current_user: Optional[dict] = Depends(get_optional_token)
):
    """
    獲取公開的旅程列表（分頁）
    """
    result = svc.get_public_trips(page, page_size, keyword)
    return result

# ============================================================================
# Trip Status 端點
# ============================================================================

@router.put("/{trip_id}/status", response_model=TripStatusUpdate)
def update_trip_status(trip_id:str, payload: TripStatusUpdate, svc: TripService = Depends(get_trip_service), current_user: dict = Depends(get_current_token)):
    """
    更新旅程狀態
    """
    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unthorised/ Invalid token")
    
    try:
        trip = svc.update_trip_status(trip_id, payload.status, user_id)
        if not trip:
          raise HTTPException(status_code=404, detail="Trip doesn't exist.")
        return trip
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

