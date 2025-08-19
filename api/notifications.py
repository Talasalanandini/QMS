from fastapi import APIRouter, Depends, Query
from typing import Optional

from api.employeemanagement import get_current_user
from services.notificationsservice import get_notifications
from models import Employee

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("", summary="Get notifications list")
def list_notifications(current_user: Employee = Depends(get_current_user)):
    items = get_notifications(current_user_id=current_user.id)
    return {"notifications": items}
