from fastapi import APIRouter, Depends, HTTPException, Body, Query, Request
from schemas import AuditScheduleSchema, AuditDetailsSchema, AuditSubmitSchema
from api.employeemanagement import admin_auth
from db.database import SessionLocal
from models import Audit, Employee, Department, Role, Token
from typing import Optional
import datetime

router = APIRouter(prefix="/audit", tags=["Audit Management"])

def audit_auth(request: Request = None):
    """Authentication for admin and auditor users only"""
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
        
        # Check if user is admin or auditor
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
        
        is_admin = admin_role and getattr(employee, 'role_id', None) == getattr(admin_role, 'id', None)
        is_auditor = auditor_role and getattr(employee, 'role_id', None) == getattr(auditor_role, 'id', None)
        
        if not (is_admin or is_auditor):
            raise HTTPException(status_code=403, detail="Access denied. Only Admin and Auditor users can access audit management.")
        
        return employee
    finally:
        session.close()

def auditor_only_auth(request: Request = None):
    """Authentication for auditor users only"""
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
        
        # Check if user is auditor only
        auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
        is_auditor = auditor_role and getattr(employee, 'role_id', None) == getattr(auditor_role, 'id', None)
        
        if not is_auditor:
            raise HTTPException(status_code=403, detail="Access denied. Only Auditor users can perform this action.")
        
        return employee
    finally:
        session.close()

@router.post("/schedule", summary="Schedule a new audit")
def schedule_audit(audit_data: AuditScheduleSchema, current_user: Employee = Depends(admin_auth)):
    session = SessionLocal()
    try:
        # Validate auditor if provided
        if audit_data.auditor_id:
            auditor = session.query(Employee).filter(Employee.id == audit_data.auditor_id).first()
            if not auditor:
                raise HTTPException(status_code=400, detail="Auditor not found")
            
            # Check if the employee is actually an auditor
            auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
            if not auditor_role or getattr(auditor, 'role_id', None) != getattr(auditor_role, 'id', None):
                raise HTTPException(status_code=400, detail="Selected employee is not an auditor")
        
        # Create new audit
        new_audit = Audit(
            title=audit_data.title,
            scope=audit_data.scope,
            type=audit_data.audit_type,
            target_department=audit_data.target_department,
            lead_auditor_id=audit_data.auditor_id,
            scheduled_date=audit_data.start_date,
            end_date=audit_data.end_date,
            status="Planned",
            created_by=current_user.id
        )
        
        session.add(new_audit)
        session.commit()
        session.refresh(new_audit)
        
        # Get auditor name for response
        auditor_name = None
        if new_audit.lead_auditor_id:
            auditor = session.query(Employee).filter(Employee.id == new_audit.lead_auditor_id).first()
            auditor_name = auditor.full_name if auditor else None
        
        return {
            "message": "Audit scheduled successfully",
            "audit": {
                "id": new_audit.id,
                "title": new_audit.title,
                "scope": new_audit.scope,
                "type": new_audit.type,
                "target_department": new_audit.target_department,
                "auditor": auditor_name,
                "start_date": new_audit.scheduled_date.date().isoformat() if new_audit.scheduled_date else None,
                "end_date": new_audit.end_date.date().isoformat() if new_audit.end_date else None,
                "status": new_audit.status
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to schedule audit: {str(e)}")
    finally:
        session.close()

@router.post("/{audit_id}/start", summary="Start audit - change status to In Progress")
def start_audit(audit_id: int, current_user: Employee = Depends(auditor_only_auth)):
    session = SessionLocal()
    try:
        # Get audit
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        
        # Check if user is the assigned auditor
        if audit.lead_auditor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the assigned auditor can start this audit")
        
        # Check if audit is in Planned status
        if audit.status != "Planned":
            raise HTTPException(status_code=400, detail=f"Audit must be in 'Planned' status to start. Current status: {audit.status}")
        
        # Update status to In Progress
        audit.status = "In Progress"
        session.commit()
        
        return {
            "message": "Audit started successfully",
            "audit_id": audit.id,
            "status": audit.status
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start audit: {str(e)}")
    finally:
        session.close()

@router.post("/{audit_id}/submit", summary="Submit audit report - change status to Completed")
def submit_audit_report(audit_id: int, submit_data: AuditSubmitSchema, current_user: Employee = Depends(auditor_only_auth)):
    session = SessionLocal()
    try:
        # Get audit
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        
        # Check if user is the assigned auditor
        if audit.lead_auditor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the assigned auditor can submit this audit")
        
        # Check if audit is in progress
        if audit.status != "In Progress":
            raise HTTPException(status_code=400, detail=f"Audit must be in 'In Progress' status to submit. Current status: {audit.status}")
        
        # Update audit details and status
        if submit_data.observations is not None:
            audit.observations = submit_data.observations
        if submit_data.findings is not None:
            audit.findings = submit_data.findings
        if submit_data.recommendations is not None:
            audit.recommendations = submit_data.recommendations
        
        # Update status to Completed
        audit.status = "Completed"
        audit.completed_at = datetime.datetime.utcnow()
        
        # Save signature and submission details
        audit.signature = submit_data.signature
        audit.signed_date = submit_data.signed_date
        audit.auditor_name = submit_data.auditor_name
        
        session.commit()
        
        return {
            "message": "Audit report submitted successfully",
            "audit_id": audit.id,
            "status": audit.status,
            "completed_at": audit.completed_at.isoformat() if audit.completed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to submit audit report: {str(e)}")
    finally:
        session.close()


@router.get("/counts", summary="Get all audit counts for admin dashboard")
def get_audit_counts(current_user: Employee = Depends(admin_auth)):
    """Get all audit counts in a single API response"""
    session = SessionLocal()
    try:
        # Get counts for each status
        completed_count = session.query(Audit).filter(Audit.status == "Completed").count()
        scheduled_count = session.query(Audit).filter(Audit.status.in_(["Planned", "Scheduled"])).count()
        in_progress_count = session.query(Audit).filter(Audit.status == "In Progress").count()
        total_count = session.query(Audit).count()
        
        return {
            "completed": completed_count,
            "scheduled": scheduled_count,
            "in_progress": in_progress_count,
            "total": total_count
        }
    finally:
        session.close()

@router.get("/upcoming", summary="Get upcoming audits for admin dashboard")
def get_upcoming_audits(
    search: Optional[str] = Query(None, description="Search by title or scope"),
    department: Optional[str] = Query(None, description="Filter by department"),
    current_user: Employee = Depends(admin_auth)
):
    """Get upcoming (scheduled/planned) audits"""
    session = SessionLocal()
    try:
        # Build query for upcoming audits (Planned or Scheduled status)
        query = session.query(Audit).filter(Audit.status.in_(["Planned", "Scheduled"])).join(
            Employee, Audit.lead_auditor_id == Employee.id, isouter=True
        ).join(
            Department, Employee.department_id == Department.id, isouter=True
        )
        
        # Apply search filter
        if search:
            query = query.filter(
                Audit.title.ilike(f"%{search}%") |
                Audit.scope.ilike(f"%{search}%") |
                Audit.id.cast(str).ilike(f"%{search}%")
            )
        
        # Apply department filter
        if department:
            query = query.filter(Department.name.ilike(f"%{department}%"))
        
        audits = query.order_by(Audit.scheduled_date.asc()).all()
        
        result = []
        for audit in audits:
            # Get lead auditor information
            lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
            
            # Get department information
            department_obj = None
            if lead_auditor:
                department_obj = session.query(Department).filter(Department.id == lead_auditor.department_id).first()
            
            result.append({
                "id": audit.id,
                "audit_id": f"AUD-{audit.id}",
                "title": audit.title,
                "scope": audit.scope,
                "type": audit.type,
                "status": audit.status,
                "auditor": lead_auditor.full_name if lead_auditor else "Unassigned",
                "scheduled_date": audit.scheduled_date.strftime("%Y-%m-%d") if audit.scheduled_date else None,
                "department": department_obj.name if department_obj else "Unknown",
                "target_department": audit.target_department
            })
        
        return result
    finally:
        session.close()

@router.get("/all-records", summary="Get all audit records for admin dashboard")
def get_all_audit_records(
    search: Optional[str] = Query(None, description="Search by title, scope, or audit ID"),
    status: Optional[str] = Query(None, description="Filter by status: Planned, In Progress, Completed"),
    department: Optional[str] = Query(None, description="Filter by department"),
    audit_type: Optional[str] = Query(None, description="Filter by audit type"),
    current_user: Employee = Depends(admin_auth)
):
    """Get all audit records with comprehensive filtering"""
    session = SessionLocal()
    try:
        # Build query with joins
        query = session.query(Audit).join(
            Employee, Audit.lead_auditor_id == Employee.id, isouter=True
        ).join(
            Department, Employee.department_id == Department.id, isouter=True
        )
        
        # Apply search filter
        if search:
            query = query.filter(
                Audit.title.ilike(f"%{search}%") |
                Audit.scope.ilike(f"%{search}%") |
                Audit.id.cast(str).ilike(f"%{search}%")
            )
        
        # Apply status filter
        if status:
            query = query.filter(Audit.status == status)
        
        # Apply department filter
        if department:
            query = query.filter(Department.name.ilike(f"%{department}%"))
        
        # Apply audit type filter
        if audit_type:
            query = query.filter(Audit.type == audit_type)
        
        audits = query.order_by(Audit.created_at.desc()).all()
        
        result = []
        for audit in audits:
            # Get lead auditor information
            lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
            
            # Get department information
            department_obj = None
            if lead_auditor:
                department_obj = session.query(Department).filter(Department.id == lead_auditor.department_id).first()
            
            result.append({
                "id": audit.id,
                "audit_id": f"AUD-{audit.id}",
                "title": audit.title,
                "scope": audit.scope,
                "type": audit.type,
                "status": audit.status,
                "auditor": lead_auditor.full_name if lead_auditor else "Unassigned",
                "scheduled_date": audit.scheduled_date.strftime("%Y-%m-%d") if audit.scheduled_date else None,
                "department": department_obj.name if department_obj else "Unknown",
                "target_department": audit.target_department,
                "created_at": audit.created_at.strftime("%Y-%m-%d") if audit.created_at else None
            })
        
        return result
    finally:
        session.close()

@router.get("/completed", summary="Get completed audits for admin dashboard")
def get_completed_audits(
    search: Optional[str] = Query(None, description="Search by title or scope"),
    department: Optional[str] = Query(None, description="Filter by department"),
    auditor: Optional[str] = Query(None, description="Filter by auditor name"),
    current_user: Employee = Depends(admin_auth)
):
    """Get completed audits with filtering"""
    session = SessionLocal()
    try:
        # Build query for completed audits only
        query = session.query(Audit).filter(Audit.status == "Completed").join(
            Employee, Audit.lead_auditor_id == Employee.id, isouter=True
        ).join(
            Department, Employee.department_id == Department.id, isouter=True
        )
        
        # Apply search filter
        if search:
            query = query.filter(
                Audit.title.ilike(f"%{search}%") |
                Audit.scope.ilike(f"%{search}%") |
                Audit.id.cast(str).ilike(f"%{search}%")
            )
        
        # Apply department filter
        if department:
            query = query.filter(Department.name.ilike(f"%{department}%"))
        
        # Apply auditor filter
        if auditor:
            query = query.filter(Employee.full_name.ilike(f"%{auditor}%"))
        
        audits = query.order_by(Audit.completed_at.desc()).all()
        
        result = []
        for audit in audits:
            # Get lead auditor information
            lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
            
            # Get department information
            department_obj = None
            if lead_auditor:
                department_obj = session.query(Department).filter(Department.id == lead_auditor.department_id).first()
            
            result.append({
                "id": audit.id,
                "audit_id": f"AUD-{audit.id}",
                "title": audit.title,
                "scope": audit.scope,
                "type": audit.type,
                "status": audit.status,
                "auditor": lead_auditor.full_name if lead_auditor else "Unknown",
                "scheduled_date": audit.scheduled_date.strftime("%Y-%m-%d") if audit.scheduled_date else None,
                "completed_date": audit.completed_at.strftime("%Y-%m-%d") if audit.completed_at else None,
                "department": department_obj.name if department_obj else "Unknown",
                "target_department": audit.target_department,
                "has_report": bool(audit.observations or audit.findings or audit.recommendations)
            })
        
        return result
    finally:
        session.close()

@router.get("/reports", summary="Get all audit reports for admin dashboard")
def get_all_reports(
    search: Optional[str] = Query(None, description="Search by title or scope"),
    department: Optional[str] = Query(None, description="Filter by department"),
    auditor: Optional[str] = Query(None, description="Filter by auditor name"),
    current_user: Employee = Depends(admin_auth)
):
    """Get all audit reports (completed audits with reports)"""
    session = SessionLocal()
    try:
        # Build query for completed audits with reports
        query = session.query(Audit).filter(
            Audit.status == "Completed",
            (Audit.observations.isnot(None) | Audit.findings.isnot(None) | Audit.recommendations.isnot(None))
        ).join(
            Employee, Audit.lead_auditor_id == Employee.id, isouter=True
        ).join(
            Department, Employee.department_id == Department.id, isouter=True
        )
        
        # Apply search filter
        if search:
            query = query.filter(
                Audit.title.ilike(f"%{search}%") |
                Audit.scope.ilike(f"%{search}%") |
                Audit.id.cast(str).ilike(f"%{search}%")
            )
        
        # Apply department filter
        if department:
            query = query.filter(Department.name.ilike(f"%{department}%"))
        
        # Apply auditor filter
        if auditor:
            query = query.filter(Employee.full_name.ilike(f"%{auditor}%"))
        
        audits = query.order_by(Audit.completed_at.desc()).all()
        
        result = []
        for audit in audits:
            # Get lead auditor information
            lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
            
            # Get department information
            department_obj = None
            if lead_auditor:
                department_obj = session.query(Department).filter(Department.id == lead_auditor.department_id).first()
            
            result.append({
                "id": audit.id,
                "audit_id": f"AUD-{audit.id}",
                "title": audit.title,
                "scope": audit.scope,
                "type": audit.type,
                "status": audit.status,
                "auditor": lead_auditor.full_name if lead_auditor else "Unknown",
                "scheduled_date": audit.scheduled_date.strftime("%Y-%m-%d") if audit.scheduled_date else None,
                "completed_date": audit.completed_at.strftime("%Y-%m-%d") if audit.completed_at else None,
                "department": department_obj.name if department_obj else "Unknown",
                "target_department": audit.target_department,
                "observations": audit.observations,
                "findings": audit.findings,
                "recommendations": audit.recommendations,
                "signature": audit.signature,
                "signed_date": audit.signed_date,
                "auditor_name": audit.auditor_name
            })
        
        return result
    finally:
        session.close()

@router.get("/search", summary="Search audits with comprehensive filtering")
def search_audits(
    q: Optional[str] = Query(None, description="Search query for title, scope, or audit ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    department: Optional[str] = Query(None, description="Filter by department"),
    audit_type: Optional[str] = Query(None, description="Filter by audit type"),
    auditor: Optional[str] = Query(None, description="Filter by auditor name"),
    date_from: Optional[str] = Query(None, description="Filter from date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter to date (YYYY-MM-DD)"),
    current_user: Employee = Depends(admin_auth)
):
    """Comprehensive search and filter API for audits"""
    session = SessionLocal()
    try:
        # Build base query
        query = session.query(Audit).join(
            Employee, Audit.lead_auditor_id == Employee.id, isouter=True
        ).join(
            Department, Employee.department_id == Department.id, isouter=True
        )
        
        # Apply search query
        if q:
            query = query.filter(
                Audit.title.ilike(f"%{q}%") |
                Audit.scope.ilike(f"%{q}%") |
                Audit.id.cast(str).ilike(f"%{q}%")
            )
        
        # Apply status filter
        if status:
            query = query.filter(Audit.status == status)
        
        # Apply department filter
        if department:
            query = query.filter(Department.name.ilike(f"%{department}%"))
        
        # Apply audit type filter
        if audit_type:
            query = query.filter(Audit.type == audit_type)
        
        # Apply auditor filter
        if auditor:
            query = query.filter(Employee.full_name.ilike(f"%{auditor}%"))
        
        # Apply date range filter
        if date_from:
            query = query.filter(Audit.scheduled_date >= date_from)
        if date_to:
            query = query.filter(Audit.scheduled_date <= date_to)
        
        audits = query.order_by(Audit.created_at.desc()).all()
        
        result = []
        for audit in audits:
            # Get lead auditor information
            lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
            
            # Get department information
            department_obj = None
            if lead_auditor:
                department_obj = session.query(Department).filter(Department.id == lead_auditor.department_id).first()
            
            result.append({
                "id": audit.id,
                "audit_id": f"AUD-{audit.id}",
                "title": audit.title,
                "scope": audit.scope,
                "type": audit.type,
                "status": audit.status,
                "auditor": lead_auditor.full_name if lead_auditor else "Unassigned",
                "scheduled_date": audit.scheduled_date.strftime("%Y-%m-%d") if audit.scheduled_date else None,
                "completed_date": audit.completed_at.strftime("%Y-%m-%d") if audit.completed_at else None,
                "department": department_obj.name if department_obj else "Unknown",
                "target_department": audit.target_department,
                "created_at": audit.created_at.strftime("%Y-%m-%d") if audit.created_at else None
            })
        
        return result
    finally:
        session.close()


@router.put("/{audit_id}/mark-completed", summary="Mark audit as completed (auditor only)")
def mark_audit_completed(audit_id: int, current_user: Employee = Depends(auditor_only_auth)):
    """Mark an audit as completed - only the assigned auditor can do this"""
    session = SessionLocal()
    try:
        # Get audit
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        
        # Check if current user is the assigned auditor
        if audit.lead_auditor_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the assigned auditor can mark this audit as completed")
        
        # Check if audit is already completed
        if audit.status == "Completed":
            raise HTTPException(status_code=400, detail="Audit is already completed")
        
        # Update status to Completed
        audit.status = "Completed"
        audit.completed_at = datetime.datetime.utcnow()
        
        # Add sample report data with current auditor's name
        audit.observations = "Sample observations for testing"
        audit.findings = "Sample findings for testing"
        audit.recommendations = "Sample recommendations for testing"
        audit.signature = "sample_signature"
        audit.signed_date = datetime.datetime.utcnow().isoformat()
        audit.auditor_name = current_user.full_name
        
        session.commit()
        
        return {
            "message": "Audit marked as completed successfully",
            "audit_id": audit.id,
            "status": audit.status,
            "completed_at": audit.completed_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to mark audit as completed: {str(e)}")
    finally:
        session.close()

@router.get("/{audit_id}", summary="Get audit details by ID")
def get_audit_details(audit_id: int, current_user: Employee = Depends(admin_auth)):
    """Get detailed information of a specific audit"""
    session = SessionLocal()
    try:
        # Get audit with joins
        audit = session.query(Audit).filter(Audit.id == audit_id).join(
            Employee, Audit.lead_auditor_id == Employee.id, isouter=True
        ).join(
            Department, Employee.department_id == Department.id, isouter=True
        ).first()
        
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        
        # Get lead auditor information
        lead_auditor = session.query(Employee).filter(Employee.id == audit.lead_auditor_id).first()
        
        # Get department information
        department_obj = None
        if lead_auditor:
            department_obj = session.query(Department).filter(Department.id == lead_auditor.department_id).first()
        
        # Get all available auditors for dropdown
        auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
        available_auditors = []
        if auditor_role:
            available_auditors = session.query(Employee).filter(
                Employee.role_id == auditor_role.id,
                Employee.status == "Active"
            ).all()
        
        # Get all departments for dropdown
        departments = session.query(Department).all()
        
        result = {
            "id": audit.id,
            "audit_id": f"AUD-{audit.id}",
            "title": audit.title,
            "scope": audit.scope,
            "type": audit.type,
            "status": audit.status,
            "target_department": audit.target_department,
            "scheduled_date": audit.scheduled_date.strftime("%Y-%m-%d") if audit.scheduled_date else None,
            "end_date": audit.end_date.strftime("%Y-%m-%d") if audit.end_date else None,
            "completed_at": audit.completed_at.strftime("%Y-%m-%d") if audit.completed_at else None,
            "observations": audit.observations,
            "findings": audit.findings,
            "recommendations": audit.recommendations,
            "signature": audit.signature,
            "signed_date": audit.signed_date,
            "auditor_name": audit.auditor_name,
            "created_at": audit.created_at.strftime("%Y-%m-%d") if audit.created_at else None,
            "updated_at": audit.updated_at.strftime("%Y-%m-%d") if audit.updated_at else None,
            "auditor": {
                "id": lead_auditor.id if lead_auditor else None,
                "name": lead_auditor.full_name if lead_auditor else "Unassigned",
                "email": lead_auditor.email if lead_auditor else None
            },
            "department": {
                "id": department_obj.id if department_obj else None,
                "name": department_obj.name if department_obj else "Unknown"
            },
            "available_auditors": [
                {
                    "id": auditor.id,
                    "name": auditor.full_name,
                    "email": auditor.email
                } for auditor in available_auditors
            ],
            "available_departments": [
                {
                    "id": dept.id,
                    "name": dept.name
                } for dept in departments
            ]
        }
        
        return result
    finally:
        session.close()

@router.put("/{audit_id}", summary="Update audit details")
def update_audit(
    audit_id: int,
    audit_data: dict,
    current_user: Employee = Depends(admin_auth)
):
    """Update audit details"""
    session = SessionLocal()
    try:
        # Get the audit
        audit = session.query(Audit).filter(Audit.id == audit_id).first()
        if not audit:
            raise HTTPException(status_code=404, detail="Audit not found")
        
        # Check if audit can be edited (not completed)
        if audit.status == "Completed":
            raise HTTPException(status_code=400, detail="Cannot edit completed audits")
        
        # Validate auditor if provided
        if "auditor_id" in audit_data and audit_data["auditor_id"]:
            auditor = session.query(Employee).filter(
                Employee.id == audit_data["auditor_id"],
                Employee.status == "Active"
            ).first()
            if not auditor:
                raise HTTPException(status_code=400, detail="Invalid auditor ID")
            
            # Check if auditor has auditor role
            auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
            if not auditor_role or auditor.role_id != auditor_role.id:
                raise HTTPException(status_code=400, detail="Selected user is not an auditor")
        
        # Update all fields that are provided
        for field, value in audit_data.items():
            if value is not None:
                # Handle date fields
                if field in ["scheduled_date", "end_date", "completed_at", "signed_date"] and value:
                    try:
                        if field == "signed_date":
                            # signed_date is stored as string in ISO format
                            audit_data[field] = value
                        else:
                            # Convert to date object for other date fields
                            audit_data[field] = datetime.datetime.strptime(value, "%Y-%m-%d").date()
                    except ValueError:
                        raise HTTPException(status_code=400, detail=f"Invalid date format for {field}")
                
                # Handle datetime fields
                elif field in ["created_at", "updated_at"] and value:
                    try:
                        audit_data[field] = datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        raise HTTPException(status_code=400, detail=f"Invalid datetime format for {field}")
                
                # Handle text fields that might be long
                elif field in ["observations", "findings", "recommendations"]:
                    audit_data[field] = str(value)
                
                # Handle all other fields
                else:
                    audit_data[field] = value
                
                setattr(audit, field, audit_data[field])
        
        # Update the updated_at timestamp
        audit.updated_at = datetime.datetime.utcnow()
        
        session.commit()
        
        # Return updated audit details
        return {
            "message": "Audit updated successfully",
            "audit_id": audit_id,
            "updated_fields": list(audit_data.keys())
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update audit: {str(e)}")
    finally:
        session.close()

