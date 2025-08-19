import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import joinedload

from db.database import SessionLocal
from models import (
    Document,
    DocumentReview,
    DocumentView,
    ChangeControlHistory,
    LoginLog,
    WorkOrderActivity,
    Employee,
)


def _apply_time_period_filter(timestamp: datetime.datetime, time_period: Optional[str]) -> bool:
    """
    Return True if the given timestamp falls inside the requested time period.

    Accepted values for time_period:
    - None or "all" → allow everything
    - "1d" → last 24 hours
    - "7d" → last 7 days
    - "30d" → last 30 days
    - "90d" → last 90 days
    """
    if not timestamp:
        return False
    if not time_period:
        return True

    normalized = time_period.lower().strip()
    # Normalize common labels to tokens
    normalized = normalized.replace(" ", "_")  # e.g., "All Time" -> "all_time"

    if normalized in {"all", "all_time", "all-time"}:
        return True

    now = datetime.datetime.utcnow()
    # Special case for today: from 00:00 UTC to now
    if normalized == "today":
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return timestamp >= start_of_day

    mapping = {
        "1d": datetime.timedelta(days=1),
        "7d": datetime.timedelta(days=7),  # last 7 days
        "30d": datetime.timedelta(days=30),  # last 30 days
        "90d": datetime.timedelta(days=90),
        "last_week": datetime.timedelta(days=7),
        "last_month": datetime.timedelta(days=30),
    }
    delta = mapping.get(normalized)
    if not delta:
        return True
    return timestamp >= now - delta


def _text_match(value: Optional[str], query: Optional[str]) -> bool:
    if not query:
        return True
    if value is None:
        return False
    return query.lower() in value.lower()


def _make_log(
    *,
    timestamp: datetime.datetime,
    user_name: str,
    user_email: Optional[str],
    module: str,
    action: str,
    description: str,
    ip_address: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "timestamp": timestamp.isoformat() if timestamp else None,
        "user": user_name,
        "user_email": user_email,
        "module": module,
        "action": action,
        "description": description,
        "ip_address": ip_address or "N/A",
    }


def get_activity_logs(
    *,
    search: Optional[str] = None,
    module: Optional[str] = None,
    action: Optional[str] = None,
    time_period: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Aggregate activity logs from multiple sources into a unified list.

    This intentionally avoids requiring a dedicated activity_logs table by
    composing events from existing domain tables.
    """
    session = SessionLocal()
    logs: List[Dict[str, Any]] = []
    try:
        # Document Reviews (review, reject, sent_to_reviewer, sent_to_approver, approve)
        review_q = (
            session.query(DocumentReview)
            .options(joinedload(DocumentReview.reviewer), joinedload(DocumentReview.document))
            .order_by(DocumentReview.created_at.desc())
        )
        for r in review_q.all():
            reviewer = r.reviewer.full_name if r.reviewer else "Unknown"
            reviewer_email = r.reviewer.email if r.reviewer else None
            doc_title = r.document.title if r.document else f"Document #{r.document_id}"
            desc = f"{reviewer} performed '{r.action}' on document '{doc_title}'"
            log = _make_log(
                timestamp=r.created_at,
                user_name=reviewer,
                user_email=reviewer_email,
                module="Document",
                action=r.action,
                description=desc,
            )
            logs.append(log)

        # Document Views
        view_q = session.query(DocumentView).order_by(DocumentView.viewed_at.desc())
        for v in view_q.all():
            viewer_email = None
            if v.viewer:
                viewer_email = v.viewer.email
            desc = f"{v.viewer_name} viewed document #{v.document_id}"
            logs.append(
                _make_log(
                    timestamp=v.viewed_at,
                    user_name=v.viewer_name,
                    user_email=viewer_email,
                    module="Document",
                    action="view",
                    description=desc,
                )
            )

        # Change Control History
        cch_q = (
            session.query(ChangeControlHistory)
            .options(joinedload(ChangeControlHistory.performed_by))
            .order_by(ChangeControlHistory.performed_at.desc())
        )
        for h in cch_q.all():
            performer = h.performed_by.full_name if h.performed_by else "Unknown"
            performer_email = h.performed_by.email if h.performed_by else None
            desc = f"{performer} {h.action} change control #{h.change_control_id}"
            logs.append(
                _make_log(
                    timestamp=h.performed_at,
                    user_name=performer,
                    user_email=performer_email,
                    module="Change Control",
                    action=h.action,
                    description=desc,
                )
            )

        # Login/Logout events
        login_q = session.query(LoginLog).order_by(LoginLog.created_at.desc())
        for lg in login_q.all():
            user: Optional[Employee] = session.query(Employee).filter(Employee.id == lg.user_id).first()
            user_name = user.full_name if user else f"User #{lg.user_id}"
            user_email = user.email if user else None
            if lg.login_time and _apply_time_period_filter(lg.login_time, time_period):
                logs.append(
                    _make_log(
                        timestamp=lg.login_time,
                        user_name=user_name,
                        user_email=user_email,
                        module="Authentication",
                        action="login",
                        description=f"{user_name} logged in",
                    )
                )
            if lg.logout_time and _apply_time_period_filter(lg.logout_time, time_period):
                logs.append(
                    _make_log(
                        timestamp=lg.logout_time,
                        user_name=user_name,
                        user_email=user_email,
                        module="Authentication",
                        action="logout",
                        description=f"{user_name} logged out",
                    )
                )

        # Work Order Activities
        try:
            wo_q = (
                session.query(WorkOrderActivity)
                .options(joinedload(WorkOrderActivity.performer))
                .order_by(WorkOrderActivity.created_at.desc())
            )
            for a in wo_q.all():
                performer_name = a.performer.full_name if a.performer else "Unknown"
                performer_email = a.performer.email if a.performer else None
                logs.append(
                    _make_log(
                        timestamp=a.created_at,
                        user_name=performer_name,
                        user_email=performer_email,
                        module="Work Order",
                        action=a.activity_type,
                        description=a.description or f"{performer_name} performed {a.activity_type}",
                    )
                )
        except Exception:
            # Table may not exist in some deployments; ignore silently
            pass

        # Time period filter (applied where not already applied)
        if time_period and time_period.lower() != "all":
            def _in_period(item: Dict[str, Any]) -> bool:
                ts_str = item.get("timestamp")
                if not ts_str:
                    return False
                ts = datetime.datetime.fromisoformat(ts_str)
                return _apply_time_period_filter(ts, time_period)

            logs = [l for l in logs if _in_period(l)]

        # Module filter
        if module:
            logs = [l for l in logs if l["module"].lower() == module.lower()]

        # Action filter
        if action:
            logs = [l for l in logs if _text_match(l.get("action"), action)]

        # Search filter across description and user fields
        if search:
            q = search.lower()
            logs = [
                l for l in logs
                if _text_match(l.get("description"), q)
                or _text_match(l.get("user"), q)  # name
                or _text_match(l.get("user_email"), q)  # email
                or _text_match(l.get("action"), q)  # action
            ]

        # Sort by timestamp desc
        def _sort_key(item: Dict[str, Any]):
            try:
                return datetime.datetime.fromisoformat(item["timestamp"]) if item.get("timestamp") else datetime.datetime.min
            except Exception:
                return datetime.datetime.min

        logs.sort(key=_sort_key, reverse=True)
        return logs
    finally:
        session.close()


def get_activity_modules() -> List[str]:
    """Return a stable list of module names used in activity logs."""
    return [
        "Document",
        "Change Control",
        "Authentication",
        "Work Order",
    ]


def get_activity_actions() -> List[str]:
    """Return common actions to help clients build filters."""
    return [
        "view",
        "review",
        "reject",
        "approve",
        "sent_to_reviewer",
        "sent_to_approver",
        "login",
        "logout",
    ]


