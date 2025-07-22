from db.database import SessionLocal
from models import Audit, Employee, Role
from fastapi import HTTPException
import datetime

def create_audit(audit_data, admin_email):
    session = SessionLocal()
    try:
        admin = session.query(Employee).filter(Employee.email == admin_email).first()
        if not admin:
            raise HTTPException(status_code=404, detail="Admin not found")
        # Validate lead auditor
        lead_auditor = None
        if audit_data.lead_auditor_id is not None:
            lead_auditor = session.query(Employee).filter(Employee.id == audit_data.lead_auditor_id).first()
            if lead_auditor is None:
                raise HTTPException(status_code=400, detail="No auditor exists with this id")
            auditor_role = session.query(Role).filter(Role.name == "Auditor").first()
            lead_auditor_role_id = getattr(lead_auditor, "role_id", None)
            auditor_role_id = getattr(auditor_role, "id", None) if auditor_role is not None else None
            if auditor_role is None or lead_auditor_role_id != auditor_role_id:
                raise HTTPException(status_code=400, detail="No auditor exists with this id")
        # Parse scheduled_date if provided
        scheduled_date = None
        if audit_data.scheduled_date:
            try:
                scheduled_date = datetime.datetime.fromisoformat(audit_data.scheduled_date)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid scheduled_date format. Use ISO format.")
        audit = Audit(
            title=audit_data.title,
            type=audit_data.type,
            status=audit_data.status,
            scheduled_date=scheduled_date,
            lead_auditor_id=audit_data.lead_auditor_id,
            scope=audit_data.scope,
            created_by=admin.id
        )
        session.add(audit)
        session.commit()
        session.refresh(audit)
        return {
            "message": "Audit created successfully",
            "audit_id": audit.id,
            "title": audit.title,
            "type": audit.type,
            "status": audit.status,
            "scheduled_date": audit.scheduled_date.date().isoformat() if audit.scheduled_date is not None else None,
            "lead_auditor": lead_auditor.full_name if lead_auditor is not None else None,
            "scope": audit.scope
        }
    finally:
        session.close()
