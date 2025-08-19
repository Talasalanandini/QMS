import datetime
import time
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import joinedload

from db.database import SessionLocal
from models import (
    CAPA, CAPAHistory, Employee, Role, CAPAStatusEnum, CAPAIssueTypeEnum, CAPAPriorityEnum
)


def _generate_capa_code() -> str:
    """Generate unique CAPA code with timestamp"""
    timestamp = int(time.time() * 1000)  # Milliseconds timestamp
    return f"CAPA-{timestamp}"


def _create_capa_history(
    session,
    capa_id: int,
    action: str,
    performed_by_id: int,
    previous_status: Optional[str] = None,
    new_status: Optional[str] = None,
    comments: Optional[str] = None,
    data: Optional[Dict] = None
):
    """Create history record for CAPA actions"""
    history = CAPAHistory(
        capa_id=capa_id,
        action=action,
        performed_by_id=performed_by_id,
        previous_status=previous_status,
        new_status=new_status,
        comments=comments,
        data=data
    )
    session.add(history)
    return history


def _normalize_issue_type(value: str) -> CAPAIssueTypeEnum:
    """Map various user inputs to CAPAIssueTypeEnum.
    Accepts case-insensitive strings and common separators (space/underscore/hyphen).
    """
    if not value:
        raise ValueError("issue_type is required")
    v = value.strip().lower().replace("_", " ").replace("-", " ")
    for enum_member in CAPAIssueTypeEnum:
        if v == enum_member.value.lower():
            return enum_member
    # Additional loose matches
    aliases = {
        "non conformance": CAPAIssueTypeEnum.non_conformance,
        "customer complaint": CAPAIssueTypeEnum.customer_complaint,
        "audit finding": CAPAIssueTypeEnum.audit_finding,
        "process improvement": CAPAIssueTypeEnum.process_improvement,
        "quality issue": CAPAIssueTypeEnum.quality_issue,
        "documentation error": CAPAIssueTypeEnum.documentation_error,
        "deviation": CAPAIssueTypeEnum.deviation,
    }
    if v in aliases:
        return aliases[v]
    raise ValueError(
        "Invalid issue_type. Allowed: "
        + ", ".join(m.value for m in CAPAIssueTypeEnum)
    )


def _normalize_priority(value: str | None) -> CAPAPriorityEnum:
    """Map to CAPAPriorityEnum; default Medium."""
    if not value:
        return CAPAPriorityEnum.medium
    v = value.strip().lower()
    mapping = {
        "low": CAPAPriorityEnum.low,
        "medium": CAPAPriorityEnum.medium,
        "high": CAPAPriorityEnum.high,
        "critical": CAPAPriorityEnum.critical,
    }
    if v in mapping:
        return mapping[v]
    raise ValueError("Invalid priority. Allowed: Low, Medium, High, Critical")


def create_capa(capa_data: dict, created_by_id: int) -> Tuple[CAPA, str]:
    """Create a new CAPA with OPEN status"""
    session = SessionLocal()
    try:
        # Generate unique CAPA code
        capa_code = _generate_capa_code()
        
        # Parse due date if provided
        due_date = None
        if capa_data.get("due_date"):
            try:
                due_date = datetime.datetime.fromisoformat(capa_data["due_date"])
            except ValueError:
                return None, "Invalid due_date format. Use ISO format (YYYY-MM-DD)"
        
        # Normalize enums
        try:
            issue_type_enum = _normalize_issue_type(capa_data["issue_title"] and capa_data["issue_type"])  # ensure presence then normalize
        except Exception:
            issue_type_enum = _normalize_issue_type(capa_data["issue_type"])  # fall back

        priority_enum = _normalize_priority(capa_data.get("priority"))

        # Validate optional assignee role if provided
        assigned_to_id = capa_data.get("assigned_to")
        if assigned_to_id is not None:
            assignee = session.query(Employee).join(Role).filter(
                Employee.id == assigned_to_id,
                Employee.deleted_at.is_(None),
                Role.name == "Employee"
            ).first()
            if not assignee:
                return None, "assigned_to must be an 'Employee' user"

        # Create CAPA
        capa = CAPA(
            capa_code=capa_code,
            issue_title=capa_data["issue_title"],
            description=capa_data["description"],
            issue_type=issue_type_enum,
            priority=priority_enum,
            status=CAPAStatusEnum.open,
            assigned_to=assigned_to_id,
            assigned_by=created_by_id,
            due_date=due_date
        )
        
        session.add(capa)
        session.commit()
        session.refresh(capa)
        
        # Create history record
        _create_capa_history(
            session=session,
            capa_id=capa.id,
            action="Created",
            performed_by_id=created_by_id,
            new_status=CAPAStatusEnum.open.value,
            comments="CAPA created"
        )
        
        # If assigned, create assignment history
        if capa.assigned_to:
            _create_capa_history(
                session=session,
                capa_id=capa.id,
                action="Assigned",
                performed_by_id=created_by_id,
                previous_status=CAPAStatusEnum.open.value,
                new_status=CAPAStatusEnum.open.value,
                comments=f"Assigned to employee ID {capa.assigned_to}"
            )
        
        session.commit()
        return capa, "CAPA created successfully"
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def assign_capa(capa_id: int, assigned_to_id: int, assigned_by_id: int) -> Tuple[CAPA, str]:
    """Assign CAPA to an employee (only employees with 'Employee' role)"""
    session = SessionLocal()
    try:
        # Verify CAPA exists
        capa = session.query(CAPA).filter(CAPA.id == capa_id, CAPA.deleted_at.is_(None)).first()
        if not capa:
            return None, "CAPA not found"
        
        # Verify assignee is an employee (has 'Employee' role)
        assignee = session.query(Employee).join(Role).filter(
            Employee.id == assigned_to_id,
            Employee.deleted_at.is_(None),
            Role.name == "Employee"
        ).first()
        
        if not assignee:
            return None, "Assignee must have 'Employee' role"
        
        # Update assignment
        previous_assignee = capa.assigned_to
        capa.assigned_to = assigned_to_id
        capa.updated_at = datetime.datetime.utcnow()
        
        # Create history record
        action = "Reassigned" if previous_assignee else "Assigned"
        comments = f"Assigned to {assignee.full_name}"
        if previous_assignee:
            prev_employee = session.query(Employee).filter(Employee.id == previous_assignee).first()
            prev_name = prev_employee.full_name if prev_employee else f"Employee #{previous_assignee}"
            comments = f"Reassigned from {prev_name} to {assignee.full_name}"
        
        _create_capa_history(
            session=session,
            capa_id=capa_id,
            action=action,
            performed_by_id=assigned_by_id,
            previous_status=capa.status.value,
            new_status=capa.status.value,
            comments=comments,
            data={"previous_assignee": previous_assignee, "new_assignee": assigned_to_id}
        )
        
        session.commit()
        session.refresh(capa)
        return capa, f"CAPA {action.lower()} successfully to {assignee.full_name}"
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def start_capa_work(capa_id: int, employee_id: int, work_data: dict) -> Tuple[CAPA, str]:
    """Employee starts working on CAPA - status changes to IN PROGRESS"""
    session = SessionLocal()
    try:
        # Verify CAPA exists and is assigned to this employee
        capa = session.query(CAPA).filter(
            CAPA.id == capa_id,
            CAPA.deleted_at.is_(None),
            CAPA.assigned_to == employee_id
        ).first()
        
        if not capa:
            return None, "CAPA not found or not assigned to you"
        
        if capa.status != CAPAStatusEnum.open and capa.status != CAPAStatusEnum.sent_back:
            return None, f"CAPA must be in OPEN or SENT BACK status. Current status: {capa.status.value}"
        
        # Update CAPA
        previous_status = capa.status
        capa.status = CAPAStatusEnum.in_progress
        capa.started_date = datetime.datetime.utcnow()
        capa.action_taken = work_data.get("action_taken")
        capa.completion_notes = work_data.get("completion_notes")
        capa.evidence_files = work_data.get("evidence_files", [])
        capa.updated_at = datetime.datetime.utcnow()
        
        # Create history record
        _create_capa_history(
            session=session,
            capa_id=capa_id,
            action="Started Work",
            performed_by_id=employee_id,
            previous_status=previous_status.value,
            new_status=CAPAStatusEnum.in_progress.value,
            comments="Work started on CAPA"
        )
        
        session.commit()
        session.refresh(capa)
        return capa, "CAPA work started successfully"
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def complete_capa(capa_id: int, employee_id: int, completion_data: dict) -> Tuple[CAPA, str]:
    """Employee marks CAPA as completed - status changes to PENDING VERIFICATION"""
    session = SessionLocal()
    try:
        # Verify CAPA exists and is assigned to this employee
        capa = session.query(CAPA).filter(
            CAPA.id == capa_id,
            CAPA.deleted_at.is_(None),
            CAPA.assigned_to == employee_id
        ).first()
        
        if not capa:
            return None, "CAPA not found or not assigned to you"
        
        if capa.status != CAPAStatusEnum.in_progress:
            return None, f"CAPA must be IN PROGRESS. Current status: {capa.status.value}"
        
        # Parse completion date
        completion_date = None
        if completion_data.get("completion_date"):
            try:
                completion_date = datetime.datetime.fromisoformat(completion_data["completion_date"])
            except ValueError:
                return None, "Invalid completion_date format. Use ISO format (YYYY-MM-DD)"
        
        # Update CAPA
        previous_status = capa.status
        capa.status = CAPAStatusEnum.pending_verification
        capa.completed_date = completion_date or datetime.datetime.utcnow()
        capa.action_taken = completion_data.get("action_taken")
        capa.completion_notes = completion_data.get("completion_notes")
        capa.evidence_files = completion_data.get("evidence_files", [])
        capa.updated_at = datetime.datetime.utcnow()
        
        # Create history record
        _create_capa_history(
            session=session,
            capa_id=capa_id,
            action="Completed",
            performed_by_id=employee_id,
            previous_status=previous_status.value,
            new_status=CAPAStatusEnum.pending_verification.value,
            comments="CAPA marked as completed and sent for review"
        )
        
        session.commit()
        session.refresh(capa)
        return capa, "CAPA completed successfully and sent for review"
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def close_capa(capa_id: int, admin_id: int) -> Tuple[CAPA, str]:
    """Admin marks CAPA as closed"""
    session = SessionLocal()
    try:
        # Verify CAPA exists and is in PENDING VERIFICATION status
        capa = session.query(CAPA).filter(
            CAPA.id == capa_id,
            CAPA.deleted_at.is_(None)
        ).first()
        
        if not capa:
            return None, "CAPA not found"
        
        if capa.status != CAPAStatusEnum.pending_verification:
            return None, f"CAPA must be PENDING VERIFICATION. Current status: {capa.status.value}"
        
        # Update CAPA
        previous_status = capa.status
        capa.status = CAPAStatusEnum.closed
        capa.closed_date = datetime.datetime.utcnow()
        capa.updated_at = datetime.datetime.utcnow()
        
        # Create history record
        _create_capa_history(
            session=session,
            capa_id=capa_id,
            action="Closed",
            performed_by_id=admin_id,
            previous_status=previous_status.value,
            new_status=CAPAStatusEnum.closed.value,
            comments="CAPA verified and closed by admin"
        )
        
        session.commit()
        session.refresh(capa)
        return capa, "CAPA closed successfully"
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def send_back_capa(capa_id: int, admin_id: int, comments: Optional[str] = None) -> Tuple[CAPA, str]:
    """Admin sends CAPA back to assigned employee - status changes to SENT BACK"""
    session = SessionLocal()
    try:
        # Verify CAPA exists and is in PENDING VERIFICATION status
        capa = session.query(CAPA).filter(
            CAPA.id == capa_id,
            CAPA.deleted_at.is_(None)
        ).first()
        
        if not capa:
            return None, "CAPA not found"
        
        if capa.status != CAPAStatusEnum.pending_verification:
            return None, f"CAPA must be PENDING VERIFICATION. Current status: {capa.status.value}"
        
        if not capa.assigned_to:
            return None, "CAPA has no assigned employee to send back to"
        
        # Update CAPA
        previous_status = capa.status
        capa.status = CAPAStatusEnum.sent_back
        capa.updated_at = datetime.datetime.utcnow()
        
        # Create history record
        _create_capa_history(
            session=session,
            capa_id=capa_id,
            action="Sent Back",
            performed_by_id=admin_id,
            previous_status=previous_status.value,
            new_status=CAPAStatusEnum.sent_back.value,
            comments=comments or "CAPA sent back for revision"
        )
        
        session.commit()
        session.refresh(capa)
        return capa, "CAPA sent back successfully"
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_capas_by_status(status: Optional[str] = None, assigned_to: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get CAPAs filtered by status and/or assigned employee"""
    session = SessionLocal()
    try:
        query = session.query(CAPA).filter(CAPA.deleted_at.is_(None))
        
        if status:
            query = query.filter(CAPA.status == status)
        
        if assigned_to:
            query = query.filter(CAPA.assigned_to == assigned_to)
        
        # Use eager loading for relationships
        query = query.options(
            joinedload(CAPA.assignee),
            joinedload(CAPA.creator)
        )
        
        capas = query.order_by(CAPA.created_at.desc()).all()
        
        # Format response
        result = []
        for capa in capas:
            result.append({
                "id": capa.id,
                "capa_code": capa.capa_code,
                "issue_title": capa.issue_title,
                "description": capa.description,
                "issue_type": capa.issue_type.value,
                "priority": capa.priority.value,
                "status": capa.status.value,
                "assigned_to": capa.assigned_to,
                "assigned_to_name": capa.assignee.full_name if capa.assignee else None,
                "assigned_by": capa.assigned_by,
                "assigned_by_name": capa.creator.full_name if capa.creator else None,
                "created_date": capa.created_date.isoformat() if capa.created_date else None,
                "due_date": capa.due_date.isoformat() if capa.due_date else None,
                "started_date": capa.started_date.isoformat() if capa.started_date else None,
                "completed_date": capa.completed_date.isoformat() if capa.completed_date else None,
                "closed_date": capa.closed_date.isoformat() if capa.closed_date else None,
                "action_taken": capa.action_taken,
                "completion_notes": capa.completion_notes,
                "evidence_files": capa.evidence_files,
                "created_at": capa.created_at.isoformat() if capa.created_at else None,
                "updated_at": capa.updated_at.isoformat() if capa.updated_at else None
            })
        
        return result
        
    finally:
        session.close()


def get_capa_by_id(capa_id: int) -> Optional[Dict[str, Any]]:
    """Get CAPA by ID with full details"""
    session = SessionLocal()
    try:
        capa = session.query(CAPA).options(
            joinedload(CAPA.assignee),
            joinedload(CAPA.creator)
        ).filter(CAPA.id == capa_id, CAPA.deleted_at.is_(None)).first()
        
        if not capa:
            return None
        
        return {
            "id": capa.id,
            "capa_code": capa.capa_code,
            "issue_title": capa.issue_title,
            "description": capa.description,
            "issue_type": capa.issue_type.value,
            "priority": capa.priority.value,
            "status": capa.status.value,
            "assigned_to": capa.assigned_to,
            "assigned_to_name": capa.assignee.full_name if capa.assignee else None,
            "assigned_by": capa.assigned_by,
            "assigned_by_name": capa.creator.full_name if capa.creator else None,
            "created_date": capa.created_date.isoformat() if capa.created_date else None,
            "due_date": capa.due_date.isoformat() if capa.due_date else None,
            "started_date": capa.started_date.isoformat() if capa.started_date else None,
            "completed_date": capa.completed_date.isoformat() if capa.completed_date else None,
            "closed_date": capa.closed_date.isoformat() if capa.closed_date else None,
            "action_taken": capa.action_taken,
            "completion_notes": capa.completion_notes,
            "evidence_files": capa.evidence_files,
            "created_at": capa.created_at.isoformat() if capa.created_at else None,
            "updated_at": capa.updated_at.isoformat() if capa.updated_at else None
        }
        
    finally:
        session.close()


def get_capa_history(capa_id: int) -> List[Dict[str, Any]]:
    """Get CAPA history/audit trail"""
    session = SessionLocal()
    try:
        history = session.query(CAPAHistory).options(
            joinedload(CAPAHistory.performed_by)
        ).filter(CAPAHistory.capa_id == capa_id).order_by(CAPAHistory.performed_at.desc()).all()
        
        result = []
        for h in history:
            result.append({
                "id": h.id,
                "capa_id": h.capa_id,
                "action": h.action,
                "performed_by_id": h.performed_by_id,
                "performed_by_name": h.performed_by.full_name if h.performed_by else "Unknown",
                "previous_status": h.previous_status,
                "new_status": h.new_status,
                "comments": h.comments,
                "data": h.data,
                "performed_at": h.performed_at.isoformat() if h.performed_at else None
            })
        
        return result
        
    finally:
        session.close()


def get_employees_for_assignment() -> List[Dict[str, Any]]:
    """Get list of employees with 'Employee' role for CAPA assignment"""
    session = SessionLocal()
    try:
        employees = session.query(Employee).join(Role).filter(
            Employee.deleted_at.is_(None),
            Role.name == "Employee"
        ).all()
        
        result = []
        for emp in employees:
            result.append({
                "id": emp.id,
                "full_name": emp.full_name,
                "email": emp.email,
                "role": emp.role_obj.name if emp.role_obj else "Unknown"
            })
        
        return result
        
    finally:
        session.close()


def get_capa_statistics() -> Dict[str, Any]:
    """Get CAPA statistics for dashboard"""
    session = SessionLocal()
    try:
        total_capas = session.query(CAPA).filter(CAPA.deleted_at.is_(None)).count()
        open_capas = session.query(CAPA).filter(
            CAPA.status == CAPAStatusEnum.open,
            CAPA.deleted_at.is_(None)
        ).count()
        in_progress_capas = session.query(CAPA).filter(
            CAPA.status == CAPAStatusEnum.in_progress,
            CAPA.deleted_at.is_(None)
        ).count()
        pending_verification_capas = session.query(CAPA).filter(
            CAPA.status == CAPAStatusEnum.pending_verification,
            CAPA.deleted_at.is_(None)
        ).count()
        closed_capas = session.query(CAPA).filter(
            CAPA.status == CAPAStatusEnum.closed,
            CAPA.deleted_at.is_(None)
        ).count()
        
        return {
            "total_capas": total_capas,
            "open_capas": open_capas,
            "in_progress_capas": in_progress_capas,
            "pending_verification_capas": pending_verification_capas,
            "closed_capas": closed_capas
        }
        
    finally:
        session.close()
