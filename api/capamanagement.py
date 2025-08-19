from fastapi import APIRouter, Depends, HTTPException, Query, Path, UploadFile, File, Form
from typing import Optional

from api.employeemanagement import admin_auth, get_current_user
from services.capaservices import (
    create_capa,
    start_capa_work,
    complete_capa,
    close_capa,
    send_back_capa,
    get_capas_by_status,
    assign_capa
)
from schemas import (
    CAPACreateSchema,
    CAPAStartWorkSchema,
    CAPACompletionSchema,
    CAPAReassignmentSchema,
    CAPAListResponseSchema
)
from models import Employee


router = APIRouter(
    prefix="/capa",
    tags=["CAPA Management"]
)


@router.post("/create", summary="Create new CAPA", response_model=dict)
def create_new_capa(
    capa_data: CAPACreateSchema,
    current_user: Employee = Depends(admin_auth)
):
    """Create a new CAPA with OPEN status (Admin only). Supports initial assignment via 'assigned_to'."""
    capa, message = create_capa(capa_data.dict(), current_user.id)
    
    if not capa:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "capa_id": capa.id,
        "capa_code": capa.capa_code
    }


@router.post("/{capa_id}/start-work", summary="Employee starts working on CAPA")
def start_work_on_capa(
    capa_id: int = Path(..., description="CAPA ID"),
    work_data: CAPAStartWorkSchema = None,
    current_user: Employee = Depends(get_current_user)
):
    """Employee starts working on CAPA - status changes to IN PROGRESS"""
    if not work_data:
        raise HTTPException(status_code=400, detail="Work data required")
    
    capa, message = start_capa_work(capa_id, current_user.id, work_data.dict())
    
    if not capa:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "capa_id": capa.id
    }


@router.post("/{capa_id}/complete", summary="Employee marks CAPA as completed (with evidence upload)")
def complete_capa_work(
    capa_id: int = Path(..., description="CAPA ID"),
    action_taken: Optional[str] = Form(None),
    completion_notes: Optional[str] = Form(None),
    completion_date: Optional[str] = Form(None),
    evidence_files: Optional[list[UploadFile]] = File(None),
    current_user: Employee = Depends(get_current_user)
):
    """Employee marks CAPA as completed using multipart form-data.

    - action_taken (optional string)
    - completion_notes (optional string)
    - completion_date (optional string YYYY-MM-DD)
    - evidence_files (0..N files)
    """
    import os

    saved_paths: list[str] = []
    if evidence_files:
        base_dir = os.path.join("uploads", "capa_evidence", str(capa_id))
        os.makedirs(base_dir, exist_ok=True)
        for f in evidence_files:
            filename = f.filename
            dest_path = os.path.join(base_dir, filename)
            with open(dest_path, "wb") as out:
                out.write(f.file.read())
            saved_paths.append(dest_path)

    payload = {
        "action_taken": action_taken,
        "completion_notes": completion_notes,
        "completion_date": completion_date,
        "evidence_files": saved_paths,
    }

    capa, message = complete_capa(capa_id, current_user.id, payload)

    if not capa:
        raise HTTPException(status_code=400, detail=message)

    return {
        "message": message,
        "capa_id": capa.id
    }


@router.post("/{capa_id}/close", summary="Admin marks CAPA as closed")
def close_capa_by_admin(
    capa_id: int = Path(..., description="CAPA ID"),
    current_user: Employee = Depends(admin_auth)
):
    """Admin marks CAPA as closed"""
    capa, message = close_capa(capa_id, current_user.id)
    
    if not capa:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "capa_id": capa.id,
        "status": capa.status.value,
        "closed_date": capa.closed_date.isoformat() if capa.closed_date else None
    }


@router.post("/{capa_id}/send-back", summary="Admin sends CAPA back to employee")
def send_capa_back(
    capa_id: int = Path(..., description="CAPA ID"),
    comments: Optional[str] = Query(None, description="Comments for sending back"),
    current_user: Employee = Depends(admin_auth)
):
    """Admin sends CAPA back to assigned employee - status changes to SENT BACK"""
    capa, message = send_back_capa(capa_id, current_user.id, comments)
    
    if not capa:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "capa_id": capa.id,
        "status": capa.status.value
    }


@router.post("/{capa_id}/reassign", summary="Admin reassigns CAPA to another employee")
def reassign_capa(
    capa_id: int = Path(..., description="CAPA ID"),
    reassignment_data: CAPAReassignmentSchema = None,
    current_user: Employee = Depends(admin_auth)
):
    """Admin reassigns CAPA to another employee (assignee must have 'Employee' role)"""
    if not reassignment_data:
        raise HTTPException(status_code=400, detail="Reassignment data required")
    
    capa, message = assign_capa(capa_id, reassignment_data.assigned_to, current_user.id)
    
    if not capa:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "capa_id": capa.id,
        "assigned_to": capa.assigned_to,
        "status": capa.status.value
    }


@router.get("/list", summary="Get all CAPAs", response_model=CAPAListResponseSchema)
def list_capas(
    status: Optional[str] = Query(None, description="Optional status filter"),
    assigned_to: Optional[int] = Query(None, description="Optional assigned employee ID")
):
    """Get all CAPAs (optionally filter by status or assignee)"""
    capas = get_capas_by_status(status=status, assigned_to=assigned_to)
    
    return {
        "capas": capas,
        "total_count": len(capas),
        "filtered_by": {
            "status": status,
            "assigned_to": assigned_to
        } if status or assigned_to else None
    }


@router.get("/completed", summary="Get completed CAPAs (ready for review)", response_model=CAPAListResponseSchema)
def get_completed_capas():
    """Get CAPAs with PENDING VERIFICATION status (Completed by employee)."""
    capas = get_capas_by_status(status="PENDING VERIFICATION")
    return {
        "capas": capas,
        "total_count": len(capas),
        "filtered_by": {"status": "PENDING VERIFICATION"}
    }
