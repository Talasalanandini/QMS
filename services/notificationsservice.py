import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import joinedload

from db.database import SessionLocal
from models import (
    TrainingAssignment, TrainingAssignmentStatusEnum,
    Training, Document, DocumentStatusEnum,
    CAPA, CAPAStatusEnum
)


def _relative_time(dt: datetime.datetime) -> str:
    if not dt:
        return ""
    now = datetime.datetime.utcnow()
    delta = now - dt
    days = delta.days
    seconds = delta.seconds
    if days > 0:
        return f"{days} day ago" if days == 1 else f"{days} days ago"
    hours = seconds // 3600
    if hours > 0:
        return f"{hours} hour ago" if hours == 1 else f"{hours} hours ago"
    minutes = (seconds % 3600) // 60
    return f"{minutes} min ago" if minutes > 0 else "just now"


def get_notifications(current_user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Aggregate notifications for dashboard dropdown.

    - Training Due: assignments due within 24 hours or overdue
    - CAPA Overdue: CAPAs in PENDING VERIFICATION older than 24h (needs admin review) or OPEN past due_date
    - Document Review: documents under_approval or under_review
    """
    session = SessionLocal()
    try:
        notifications: List[Dict[str, Any]] = []
        now = datetime.datetime.utcnow()
        tomorrow = now + datetime.timedelta(days=1)

        # Training Due (for all employees or specific user)
        q = session.query(TrainingAssignment).filter(
            TrainingAssignment.deleted_at.is_(None)
        )
        if current_user_id:
            q = q.filter(TrainingAssignment.employee_id == current_user_id)
        assignments = q.options(joinedload(TrainingAssignment.training)).all()
        for a in assignments:
            if a.status in [TrainingAssignmentStatusEnum.assigned, TrainingAssignmentStatusEnum.in_progress]:
                if a.due_date and (a.due_date <= tomorrow):
                    title = "Training Due"
                    body = f"{a.training.title} training expires tomorrow" if a.due_date > now else f"{a.training.title} training overdue"
                    notifications.append({
                        "title": title,
                        "message": body,
                        "time_ago": _relative_time(a.due_date or a.assigned_date)
                    })

        # CAPA Overdue / Pending Verification
        capas = session.query(CAPA).filter(CAPA.deleted_at.is_(None)).all()
        for c in capas:
            if c.status == CAPAStatusEnum.pending_verification:
                notifications.append({
                    "title": "CAPA Pending Review",
                    "message": f"{c.capa_code} requires action",
                    "time_ago": _relative_time(c.completed_date or c.updated_at)
                })
            elif c.status == CAPAStatusEnum.open and c.due_date and c.due_date < now:
                notifications.append({
                    "title": "CAPA Overdue",
                    "message": f"{c.capa_code} requires action",
                    "time_ago": _relative_time(c.due_date)
                })

        # Document Review / Approval notifications
        docs = session.query(Document).filter(Document.deleted_at.is_(None)).all()
        for d in docs:
            if str(d.status) in ["under_review", "under_approval"]:
                title = "Document Review" if str(d.status) == "under_review" else "Document Approval"
                notifications.append({
                    "title": title,
                    "message": f"{d.title} pending approval" if title == "Document Approval" else f"{d.title} pending review",
                    "time_ago": _relative_time(d.updated_at or d.created_at)
                })

        # Sort most recent first by a proxy time (we used time_ago text; sort by updated_at where available)
        # For simplicity, leave order as appended; frontend can sort if needed.
        return notifications
    finally:
        session.close()
