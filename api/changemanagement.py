from fastapi import APIRouter, HTTPException, Depends, Request, Query, Path, Body
from schemas import (
    ChangeControlCreateSchema, 
    ChangeControlResponseSchema,
    ChangeControlReviewSchema,
    ChangeControlApprovalSchema
)
from services.changecontrolservice import (
    create_change_control,
    get_change_control_by_id,
    review_change_control,
    approve_change_control,
    get_approved_documents,
    get_change_controls_for_reviewer,
    get_change_controls_for_approver,
    get_change_control_for_review,
    get_change_control_for_approval,
    get_change_control_dashboard_metrics
)
from api.employeemanagement import admin_auth, reviewer_auth, approver_auth, admin_or_employee_auth
from models import Employee
from sqlalchemy.orm import Session
from db.database import SessionLocal
from typing import Optional
from models import ChangeControl, ChangeStatusEnum, ChangeTypeEnum
from sqlalchemy.orm import joinedload

router = APIRouter(
    prefix="/change-control",
    tags=["Change Control Management"]
)

# Import authentication functions from user management
from api.usermanagement import get_current_user

def get_user_role(request: Request) -> str:
    """Get the role of the current user"""
    employee = get_current_user(request)
    session: Session = SessionLocal()
    try:
        from models import Role
        role = session.query(Role).filter(Role.id == employee.role_id).first()
        if role:
            return role.name
        return "Employee"
    finally:
        session.close()

# ===== CORE CHANGE CONTROL ENDPOINTS =====

@router.post("/create", summary="Create new change control request")
def create_change_control_request(
    change_data: ChangeControlCreateSchema, 
    current_user: Employee = Depends(admin_or_employee_auth)
):
    """Create a new change control request and automatically submit for review"""
    try:
        change_control, message = create_change_control(change_data.dict(), current_user.id)
        
        if not change_control:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "message": message,
            "change_control_id": change_control.id,
            "status": change_control.status.value,
            "next_action": "Reviewer will review this request"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create change control: {str(e)}")

@router.get("/{change_control_id}", summary="Get change control details")
def get_change_control_details(
    request: Request,
    change_control_id: int = Path(..., description="Change control ID"),
    current_user: Employee = Depends(admin_or_employee_auth)
):
    """Get detailed information about a specific change control request"""
    try:
        user_role = get_user_role(request)
        change_control = get_change_control_by_id(change_control_id, current_user.id, user_role)
        
        if not change_control:
            raise HTTPException(status_code=404, detail="Change control not found or access denied")
        
        return change_control
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch change control details: {str(e)}")

# ===== REVIEW WORKFLOW ENDPOINTS =====

@router.get("/review/assigned", summary="Get change controls assigned for review")
def get_assigned_for_review(
    current_user: Employee = Depends(reviewer_auth),
    status: Optional[str] = Query(None, description="Filter by status (default: submitted)")
):
    """Get change control requests assigned to the current user that need review (status: submitted)"""
    try:
        change_controls = get_change_controls_for_reviewer(current_user.id, status=status)
        
        return change_controls
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch assigned change controls: {str(e)}")

@router.get("/review/{change_control_id}/details", summary="Get change control details for review")
def get_review_details(
    change_control_id: int = Path(..., description="Change control ID"),
    current_user: Employee = Depends(reviewer_auth)
):
    """Get detailed information about a change control request for review"""
    try:
        change_control = get_change_control_for_review(change_control_id, current_user.id)
        
        if not change_control:
            raise HTTPException(status_code=404, detail="Change control not found or not assigned to you for review")
        
        return change_control
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch review details: {str(e)}")

@router.post("/{change_control_id}/review", summary="Review change control request")
def review_change_control_request(
    change_control_id: int = Path(..., description="Change control ID"),
    review_data: ChangeControlReviewSchema = Body(...),
    current_user: Employee = Depends(reviewer_auth)
):
    """Review a change control request (approve/reject for review)"""
    try:
        # Validate that the change control is assigned to this reviewer
        change_control = get_change_control_for_review(change_control_id, current_user.id)
        if not change_control:
            raise HTTPException(status_code=404, detail="Change control not found or not assigned to you for review")
        
        success, message = review_change_control(
            change_control_id, 
            current_user.id, 
            review_data.action, 
            review_data.comments
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "message": message, 
            "change_control_id": change_control_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to review change control: {str(e)}")

# ===== APPROVAL WORKFLOW ENDPOINTS =====

@router.get("/approve/ready", summary="Get change controls ready for approval")
def get_ready_for_approval(
    current_user: Employee = Depends(approver_auth)
):
    """Get change control requests ready for approval (status = reviewed)"""
    try:
        change_controls = get_change_controls_for_approver(current_user.id)
        
        return {
            "total_count": len(change_controls),
            "change_controls": change_controls
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch change controls ready for approval: {str(e)}")

@router.get("/approve/{change_control_id}/details", summary="Get change control details for approval")
def get_approval_details(
    change_control_id: int = Path(..., description="Change control ID"),
    current_user: Employee = Depends(approver_auth)
):
    """Get detailed information about a change control request for approval"""
    try:
        change_control = get_change_control_for_approval(change_control_id, current_user.id)
        
        if not change_control:
            raise HTTPException(status_code=404, detail="Change control not found or not ready for your approval")
        
        return change_control
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch approval details: {str(e)}")

@router.post("/{change_control_id}/approve", summary="Approve/reject change control request")
def approve_change_control_request(
    change_control_id: int = Path(..., description="Change control ID"),
    approval_data: ChangeControlApprovalSchema = Body(...),
    current_user: Employee = Depends(approver_auth)
):
    """Approve or reject a change control request (final decision)"""
    try:
        # Validate that the change control is ready for approval by this approver
        change_control = get_change_control_for_approval(change_control_id, current_user.id)
        if not change_control:
            raise HTTPException(status_code=404, detail="Change control not found or not ready for your approval")
        
        success, message = approve_change_control(
            change_control_id, 
            current_user.id, 
            approval_data.action, 
            approval_data.comments
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "message": message, 
            "change_control_id": change_control_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to approve change control: {str(e)}")

# ===== SUPPORTING ENDPOINTS =====

@router.get("/documents/approved", summary="Get approved documents for change control")
def get_approved_documents_for_change_control(
    current_user: Employee = Depends(admin_or_employee_auth)
):
    """Get list of approved documents that can be related to change control requests"""
    try:
        documents = get_approved_documents()
        return {
            "total_documents": len(documents),
            "documents": documents
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch approved documents: {str(e)}")

@router.get("/dashboard/metrics", summary="Get change control dashboard metrics")
def get_change_control_dashboard_metrics_endpoint(
    current_user: Employee = Depends(admin_auth)
):
    """Get dashboard metrics for change control requests (Total, Pending Review, Pending Approval, Approved) - Admin Only"""
    try:
        metrics = get_change_control_dashboard_metrics()
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch dashboard metrics: {str(e)}")

