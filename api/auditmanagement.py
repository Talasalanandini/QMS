from fastapi import APIRouter, Depends, HTTPException, Body, Query, Request, UploadFile, File
from services.auditservice import create_audit
from schemas import AuditCreateSchema, AuditEditSchema, FeedbackCreateSchema
from api.employeemanagement import admin_auth
from db.database import SessionLocal
from models import Audit, Employee, Department, Role, Token, Feedback
from typing import Optional
import datetime
from services.profileservice import upload_avatar
from api.profilemanagemet import get_current_user

router = APIRouter(prefix="/audit", tags=["Audit Management"])

def auditor_auth(request: Request = None):
    session = SessionLocal()
    try:
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        access_token = authorization.split(" ", 1)[1]
        token_obj = session.query(Token).filter(Token.token == access_token, Token.revoked == 0).first()
        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid or revoked token")
        employee = session.query(Employee).filter(Employee.id == token_obj.user_id).first()
        if employee is None:
            raise HTTPException(status_code=401, detail="User not found")
        auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
        if auditor_role is None or getattr(employee, 'role_id', None) != getattr(auditor_role, 'id', None):
            raise HTTPException(status_code=403, detail="Not an auditor user")
        return employee.email
    finally:
        session.close()

@router.post("/create")
def create_audit_api(audit_data: AuditCreateSchema, admin_email: str = Depends(admin_auth)):
    return create_audit(audit_data, admin_email)

@router.get("/auditors", summary="List all employees with Auditor role")
def list_auditors():
    session = SessionLocal()
    try:
        auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
        if not auditor_role:
            return []
        auditors = session.query(Employee).filter(Employee.role_id == auditor_role.id).all()
        return [
            {"id": auditor.id, "full_name": auditor.full_name, "email": auditor.email}
            for auditor in auditors
        ]
    finally:
        session.close()

@router.get("/all", summary="List all audits")
def list_audits(search: Optional[str] = None, department: Optional[str] = None, status: Optional[str] = None):
    session = SessionLocal()
    try:
        query = session.query(Audit).join(Employee, Audit.lead_auditor_id == Employee.id, isouter=True).join(Department, Employee.department_id == Department.id, isouter=True)
        if search:
            query = query.filter(Audit.title.ilike(f"%{search}%"))
        if department:
            query = query.filter(Department.name == department)
        if status:
            query = query.filter(Audit.status == status)
        audits = query.all()
        result = []
        for audit in audits:
            lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
            department_obj = session.query(Department).filter(Department.id == lead_auditor.department_id).first() if lead_auditor else None
            result.append({
                "id": audit.id,
                "title": audit.title,
                "type": audit.type,
                "status": audit.status,
                "scheduled_date": audit.scheduled_date.date().isoformat() if audit.scheduled_date is not None else None,
                "lead_auditor": lead_auditor.full_name if lead_auditor else None,
                "scope": audit.scope
            })
        return result
    finally:
        session.close()


@router.get("/by-title/{title}", summary="View all audits by title")
def view_audits_by_title(title: str):
    session = SessionLocal()
    try:
        audits = session.query(Audit).filter(Audit.title == title).all()
        if not audits:
            raise HTTPException(status_code=404, detail="No audits found with this title")
        result = []
        for audit in audits:
            lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
            result.append({
                "id": audit.id,
                "title": audit.title,
                "type": audit.type,
                "status": audit.status,
                "scheduled_date": audit.scheduled_date.date().isoformat() if audit.scheduled_date is not None else None,
                "lead_auditor": lead_auditor.full_name if lead_auditor else None,
                "scope": audit.scope
            })
        return result
    finally:
        session.close()

@router.put("/{audit_id}", summary="Edit audit")
def edit_audit(audit_id: int, audit_data: AuditEditSchema):
    session = SessionLocal()
    try:
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        data = audit_data.dict(exclude_unset=True)
        # Update fields if provided
        if "title" in data:
            audit.title = data["title"]
        if "type" in data:
            audit.type = data["type"]
        if "status" in data:
            audit.status = data["status"]
        if "scheduled_date" in data:
            try:
                setattr(audit, "scheduled_date", datetime.datetime.fromisoformat(data["scheduled_date"]))
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid scheduled_date format. Use ISO format.")
        if "lead_auditor_id" in data:
            lead_auditor = session.query(Employee).filter(Employee.id == data["lead_auditor_id"]).first()
            if not lead_auditor:
                raise HTTPException(status_code=400, detail="No auditor exists with this id")
            auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
            lead_auditor_role_id = getattr(lead_auditor, "role_id", None)
            auditor_role_id = getattr(auditor_role, "id", None) if auditor_role is not None else None
            if auditor_role is None or lead_auditor_role_id != auditor_role_id:
                raise HTTPException(status_code=400, detail="No auditor exists with this id")
            audit.lead_auditor_id = data["lead_auditor_id"]
        if "scope" in data:
            audit.scope = data["scope"]
        session.commit()
        lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
        return {
            "id": audit.id,
            "title": audit.title,
            "type": audit.type,
            "status": audit.status,
            "scheduled_date": audit.scheduled_date.date().isoformat() if audit.scheduled_date is not None else None,
            "lead_auditor": lead_auditor.full_name if lead_auditor else None,
            "scope": audit.scope
        }
    finally:
        session.close()

@router.patch("/{audit_id}/status", summary="Change status of audit")
def change_audit_status(audit_id: int, status: str = Query(..., regex="^(Scheduled|In Progress|Completed)$"), username: str = Depends(auditor_auth)):
    session = SessionLocal()
    try:
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        audit.status = status
        session.commit()
        return {"message": f"Audit status changed to {status}", "id": audit.id, "status": audit.status}
    finally:
        session.close()

@router.get("/status-counts", summary="Get audit counts by status")
def get_audit_status_counts():
    session = SessionLocal()
    try:
        total = session.query(Audit).count()
        scheduled = session.query(Audit).filter(Audit.status == "Scheduled").count()
        in_progress = session.query(Audit).filter(Audit.status == "In Progress").count()
        completed = session.query(Audit).filter(Audit.status == "Completed").count()
        return {
            "total": total,
            "Scheduled": scheduled,
            "In Progress": in_progress,
            "Completed": completed
        }
    finally:
        session.close()

@router.post("/feedback", summary="Submit feedback for an audit")
def submit_feedback(feedback_data: FeedbackCreateSchema, username: str = Depends(auditor_auth)):
    session = SessionLocal()
    try:
        # Get auditor by email
        auditor = session.query(Employee).filter(Employee.email == username).first()
        if not auditor:
            raise HTTPException(status_code=404, detail="Auditor not found")
        # Check audit exists and is completed
        audit = session.query(Audit).filter(Audit.id == feedback_data.audit_id).first()
        if not audit or audit.status != "Completed":
            raise HTTPException(status_code=400, detail="Audit not found or not completed")
        # Save feedback
        feedback = Feedback(
            audit_id=feedback_data.audit_id,
            auditor_id=auditor.id,
            feedback=feedback_data.feedback
        )
        session.add(feedback)
        session.commit()
        return {"message": "Feedback submitted successfully"}
    finally:
        session.close()

@router.post("/upload-avatar")
def upload_avatar_api(
    file: UploadFile = File(...),
    current_user: Employee = Depends(get_current_user)
):
    return upload_avatar(file, current_user)
