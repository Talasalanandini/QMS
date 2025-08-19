from fastapi import APIRouter, Depends, Query
from typing import Optional

from api.employeemanagement import admin_auth
from services.activutylogsservices import (
    get_activity_logs,
    get_activity_modules,
    get_activity_actions,
)


router = APIRouter(
    prefix="/activity-logs",
    tags=["Activity Logs"],
    dependencies=[Depends(admin_auth)],
)


@router.get("", summary="List activity logs")
def list_activity_logs(
    search: Optional[str] = Query(None, description="Free text across description, user name, user email, and action"),
    module: Optional[str] = Query(None, description="Filter by module name"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    time_period: Optional[str] = Query(
        None,
        description="Time window: All Time | Today | Last Week | Last Month (also supports 1d, 7d, 30d, 90d)",
    ),
):
    logs = get_activity_logs(
        search=search,
        module=module,
        action=action,
        time_period=time_period,
    )
    return {"logs": logs, "total_count": len(logs)}



