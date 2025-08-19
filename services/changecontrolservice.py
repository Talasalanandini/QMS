import datetime
from typing import List, Optional, Dict, Any, Tuple
from db.database import SessionLocal
from models import (
    ChangeControl, ChangeControlHistory, Employee, Document, 
    ChangeTypeEnum, ChangeStatusEnum, DocumentStatusEnum
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload


def create_change_control(change_data: dict, requester_id: int) -> Tuple[ChangeControl, str]:
    """Create a new change control request"""
    print("=== DEBUG: create_change_control function called ===")
    print(f"=== DEBUG: change_data: {change_data} ===")
    print(f"=== DEBUG: requester_id: {requester_id} ===")
    
    session = SessionLocal()
    try:
        # Handle case-insensitive change_type input
        change_type_input = change_data["change_type"]
        print(f"DEBUG: Received change_type_input: '{change_type_input}' (type: {type(change_type_input)})")
        
        try:
            # Try exact match first
            change_type = ChangeTypeEnum(change_type_input)
            print(f"DEBUG: Exact match found: {change_type}")
        except ValueError:
            # Try case-insensitive match
            change_type_lower = change_type_input.lower()
            print(f"DEBUG: Trying case-insensitive match for: '{change_type_lower}'")
            for enum_value in ChangeTypeEnum:
                print(f"DEBUG: Checking enum_value: {enum_value.name} = {enum_value.value}")
                if enum_value.value.lower() == change_type_lower:
                    change_type = enum_value
                    print(f"DEBUG: Case-insensitive match found: {change_type}")
                    break
            else:
                # If no match found, raise a helpful error
                valid_types = [e.value for e in ChangeTypeEnum]
                raise ValueError(f"Invalid change_type: '{change_type_input}'. Valid values are: {valid_types}")
        
        print(f"DEBUG: Final change_type being used: {change_type} (value: {change_type.value})")
        print(f"DEBUG: change_type type: {type(change_type)}")
        print(f"DEBUG: change_type.name: {change_type.name}")
        print(f"DEBUG: change_type.value: {change_type.value}")
        
        # Create the change control
        change_control = ChangeControl(
            title=change_data["title"],
            description=change_data["description"],
            change_type=change_type,
            related_document_id=change_data.get("related_document_id"),
            reviewer_id=change_data["reviewer_id"],
            approver_id=change_data["approver_id"],
            requester_id=requester_id,
            status=ChangeStatusEnum.submitted
        )
        
        print(f"DEBUG: After creating ChangeControl object:")
        print(f"DEBUG: change_control.change_type: {change_control.change_type}")
        print(f"DEBUG: change_control.change_type.value: {change_control.change_type.value if change_control.change_type else 'None'}")
        
        session.add(change_control)
        session.commit()
        session.refresh(change_control)
        
        # Create history record
        history = ChangeControlHistory(
            change_control_id=change_control.id,
            action="Submitted",
            performed_by_id=requester_id,
            comments="Change control request submitted",
            previous_status=None,
            new_status=ChangeStatusEnum.submitted
        )
        session.add(history)
        session.commit()
        # Ensure the returned instance is fully usable after the session closes
        session.refresh(change_control)
        session.expunge(change_control)
        
        return change_control, "Change control request created successfully"
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_change_control_by_id(change_control_id: int, user_id: int, user_role: str) -> Optional[Dict[str, Any]]:
    """Get change control details by ID with access control"""
    session = SessionLocal()
    try:
        # Load change control with relationships
        change_control = session.query(ChangeControl).options(
            joinedload(ChangeControl.requester),
            joinedload(ChangeControl.reviewer),
            joinedload(ChangeControl.approver),
            joinedload(ChangeControl.related_document)
        ).filter(ChangeControl.id == change_control_id).first()
        
        if not change_control:
            return None
            
        # Check access control based on user role and relationship to the change control
        if user_role == "Admin":
            pass  # Admin can access all
        elif user_role == "Reviewer" and change_control.reviewer_id == user_id:
            pass  # Reviewer can access their assigned changes
        elif user_role == "Approver" and change_control.approver_id == user_id:
            pass  # Approver can access their assigned changes
        elif change_control.requester_id == user_id:
            pass  # Requester can access their own changes
        else:
            return None  # Access denied
            
        return {
            "id": change_control.id,
            "title": change_control.title,
            "description": change_control.description,
            "change_type": change_control.change_type.value if change_control.change_type else None,
            "related_document_id": change_control.related_document_id,
            "related_document_name": change_control.related_document.title if change_control.related_document else None,
            "reviewer_id": change_control.reviewer_id,
            "reviewer_name": change_control.reviewer.full_name if change_control.reviewer else None,
            "approver_id": change_control.approver_id,
            "approver_name": change_control.approver.full_name if change_control.approver else None,
            "requester_id": change_control.requester_id,
            "requester_name": change_control.requester.full_name if change_control.requester else None,
            "status": change_control.status.value if change_control.status else None,
            "review_comments": change_control.review_comments,
            "approval_comments": change_control.approval_comments,
            "review_date": change_control.review_date.strftime("%Y-%m-%d %H:%M:%S") if change_control.review_date else None,
            "approval_date": change_control.approval_date.strftime("%Y-%m-%d %H:%M:%S") if change_control.approval_date else None,
            "implementation_date": change_control.implementation_date.strftime("%Y-%m-%d %H:%M:%S") if change_control.implementation_date else None,
            "created_at": change_control.created_at.strftime("%Y-%m-%d %H:%M:%S") if change_control.created_at else None,
            "updated_at": change_control.updated_at.strftime("%Y-%m-%d %H:%M:%S") if change_control.updated_at else None
        }
        
    finally:
        session.close()


def review_change_control(change_control_id: int, reviewer_id: int, action: str, comments: str) -> Tuple[bool, str]:
    """Review a change control request (approve/reject for review)"""
    session = SessionLocal()
    try:
        change_control = session.query(ChangeControl).filter(ChangeControl.id == change_control_id).first()
        
        if not change_control:
            return False, "Change control not found"
            
        if change_control.reviewer_id != reviewer_id:
            return False, "You are not authorized to review this change control"
            
        if change_control.status != ChangeStatusEnum.submitted:
            return False, "Change control is not in submitted status for review"
            
        # Update status based on action
        if action.lower() == "approve":
            new_status = ChangeStatusEnum.reviewed
            change_control.review_comments = comments
            change_control.review_date = datetime.datetime.utcnow()
            action_text = "Reviewed"
        elif action.lower() == "reject":
            new_status = ChangeStatusEnum.rejected
            change_control.review_comments = comments
            change_control.review_date = datetime.datetime.utcnow()
            action_text = "Rejected"
        else:
            return False, "Invalid action. Use 'approve' or 'reject'"
            
        previous_status = change_control.status
        change_control.status = new_status
        change_control.updated_at = datetime.datetime.utcnow()
        
        # Create history record
        history = ChangeControlHistory(
            change_control_id=change_control.id,
            action=action_text,
            performed_by_id=reviewer_id,
            comments=comments,
            previous_status=previous_status,
            new_status=new_status
        )
        
        session.add(history)
        session.commit()
        
        return True, f"Change control {action_text.lower()} successfully"
        
    except Exception as e:
        session.rollback()
        return False, f"Failed to review change control: {str(e)}"
    finally:
        session.close()


def approve_change_control(change_control_id: int, approver_id: int, action: str, comments: str) -> Tuple[bool, str]:
    """Approve or reject a change control request (final approval)"""
    session = SessionLocal()
    try:
        change_control = session.query(ChangeControl).filter(ChangeControl.id == change_control_id).first()
        
        if not change_control:
            return False, "Change control not found"
            
        if change_control.approver_id != approver_id:
            return False, "You are not authorized to approve this change control"
            
        if change_control.status != ChangeStatusEnum.reviewed:
            return False, "Change control must be reviewed before approval"
            
        # Update status based on action
        if action.lower() == "approve":
            new_status = ChangeStatusEnum.approved
            change_control.approval_comments = comments
            change_control.approval_date = datetime.datetime.utcnow()
            action_text = "Approved"
        elif action.lower() == "reject":
            new_status = ChangeStatusEnum.rejected
            change_control.approval_comments = comments
            change_control.approval_date = datetime.datetime.utcnow()
            action_text = "Rejected"
        else:
            return False, "Invalid action. Use 'approve' or 'reject'"
            
        previous_status = change_control.status
        change_control.status = new_status
        change_control.updated_at = datetime.datetime.utcnow()
        
        # Create history record
        history = ChangeControlHistory(
            change_control_id=change_control.id,
            action=action_text,
            performed_by_id=approver_id,
            comments=comments,
            previous_status=previous_status,
            new_status=new_status
        )
        
        session.add(history)
        session.commit()
        
        return True, f"Change control {action_text.lower()} successfully"
        
    except Exception as e:
        session.rollback()
        return False, f"Failed to approve change control: {str(e)}"
    finally:
        session.close()


def get_approved_documents() -> List[Dict[str, Any]]:
    """Get list of approved documents that can be related to change control requests"""
    session = SessionLocal()
    try:
        documents = session.query(Document).filter(
            Document.status == DocumentStatusEnum.approved,
            Document.deleted_at.is_(None)
        ).all()
        
        return [
            {
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "version": doc.version,
                "uploaded_by": doc.uploaded_by,
                "status": doc.status.value if doc.status else None,
                "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S") if doc.created_at else None
            }
            for doc in documents
        ]
        
    finally:
        session.close()


def get_change_control_details(change_control_id: int) -> Optional[Dict[str, Any]]:
    """Get change control details (legacy function for backward compatibility)"""
    session = SessionLocal()
    try:
        change_control = session.query(ChangeControl).filter(ChangeControl.id == change_control_id).first()
        if not change_control:
            return None
        return {
            "id": change_control.id,
            "title": change_control.title,
            "change_type": change_control.change_type.value if change_control.change_type else None,
            "requested_by": change_control.requester.full_name if change_control.requester else None,
            "reviewer": change_control.reviewer.full_name if change_control.reviewer else None,
            "approver": change_control.approver.full_name if change_control.approver else None,
            "status": change_control.status.value if change_control.status else None,
            "created_at": change_control.created_at.strftime("%b %d, %Y") if change_control.created_at else None,
        }
    finally:
        session.close()


def get_all_change_controls(status: Optional[str] = None, change_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all change control requests with optional filtering"""
    session = SessionLocal()
    try:
        query = session.query(ChangeControl).options(
            joinedload(ChangeControl.requester),
            joinedload(ChangeControl.reviewer),
            joinedload(ChangeControl.approver),
            joinedload(ChangeControl.related_document)
        ).filter(ChangeControl.deleted_at.is_(None))
        
        # Apply filters if provided
        if status:
            try:
                status_enum = ChangeStatusEnum(status.lower())
                query = query.filter(ChangeControl.status == status_enum)
            except ValueError:
                pass  # Invalid status, ignore filter
        
        if change_type:
            try:
                type_enum = ChangeTypeEnum(change_type.lower())
                query = query.filter(ChangeControl.change_type == type_enum)
            except ValueError:
                pass  # Invalid change_type, ignore filter
        
        # Order by creation date (newest first)
        query = query.order_by(ChangeControl.created_at.desc())
        
        change_controls = query.all()
        
        return [
            {
                "id": cc.id,
                "title": cc.title,
                "change_type": cc.change_type.value if cc.change_type else None,
                "requested_by": cc.requester.full_name if cc.requester else None,
                "reviewer": cc.reviewer.full_name if cc.reviewer else None,
                "approver": cc.approver.full_name if cc.approver else None,
                "status": cc.status.value if cc.status else None,
                "created": cc.created_at.strftime("%b %d, %Y") if cc.created_at else None,
                "description": cc.description,
                "related_document_id": cc.related_document_id,
                "related_document_name": cc.related_document.title if cc.related_document else None,
                "review_comments": cc.review_comments,
                "approval_comments": cc.approval_comments,
                "review_date": cc.review_date.strftime("%Y-%m-%d %H:%M:%S") if cc.review_date else None,
                "approval_date": cc.approval_date.strftime("%Y-%m-%d %H:%M:%S") if cc.approval_date else None,
                "implementation_date": cc.implementation_date.strftime("%Y-%m-%d %H:%M:%S") if cc.implementation_date else None,
                "updated_at": cc.updated_at.strftime("%Y-%m-%d %H:%M:%S") if cc.updated_at else None
            }
            for cc in change_controls
        ]
        
    finally:
        session.close()


def get_change_controls_for_reviewer(reviewer_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get change control requests assigned to a specific reviewer"""
    session = SessionLocal()
    try:
        query = session.query(ChangeControl).options(
            joinedload(ChangeControl.requester),
            joinedload(ChangeControl.related_document)
        ).filter(
            ChangeControl.deleted_at.is_(None),
            ChangeControl.reviewer_id == reviewer_id,
            ChangeControl.status == ChangeStatusEnum.submitted  # Only show submitted status for review
        )
        
        # Filter by status if provided (additional filtering)
        if status:
            try:
                status_enum = ChangeStatusEnum(status.lower())
                query = query.filter(ChangeControl.status == status_enum)
            except ValueError:
                pass
        
        # Order by creation date (newest first)
        query = query.order_by(ChangeControl.created_at.desc())
        
        change_controls = query.all()
        
        return [
            {
                "id": cc.id,
                "title": cc.title,
                "change_type": cc.change_type.value if cc.change_type else None,
                "document": f"{cc.related_document.title} (DOC-{cc.related_document.id})" if cc.related_document else None,
                "submitted_by": cc.requester.full_name if cc.requester else None,
                "status": cc.status.value if cc.status else None,
                "submitted_on": cc.created_at.strftime("%b %d, %Y") if cc.created_at else None,
                "description": cc.description,
                "related_document_id": cc.related_document_id
            }
            for cc in change_controls
        ]
        
    finally:
        session.close()


def get_change_controls_for_approver(approver_id: int, status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get change control requests ready for approval (status = reviewed)"""
    session = SessionLocal()
    try:
        query = session.query(ChangeControl).options(
            joinedload(ChangeControl.requester),
            joinedload(ChangeControl.reviewer),
            joinedload(ChangeControl.related_document)
        ).filter(
            ChangeControl.deleted_at.is_(None),
            ChangeControl.approver_id == approver_id,
            ChangeControl.status == ChangeStatusEnum.reviewed
        )
        
        # Order by review date (newest first)
        query = query.order_by(ChangeControl.review_date.desc())
        
        change_controls = query.all()
        
        return [
            {
                "id": cc.id,
                "title": cc.title,
                "change_type": cc.change_type.value if cc.change_type else None,
                "department": cc.related_document.title if cc.related_document else None,
                "submitted_by": cc.requester.full_name if cc.requester else None,
                "reviewed_by": cc.reviewer.full_name if cc.reviewer else None,
                "status": cc.status.value if cc.status else None,
                "last_updated": cc.review_date.strftime("%b %d, %Y") if cc.review_date else None,
                "description": cc.description,
                "related_document_id": cc.related_document_id,
                "review_comments": cc.review_comments
            }
            for cc in change_controls
        ]
        
    finally:
        session.close()


def get_change_control_for_review(change_control_id: int, reviewer_id: int) -> Optional[Dict[str, Any]]:
    """Get change control details for review with all necessary information"""
    session = SessionLocal()
    try:
        change_control = session.query(ChangeControl).options(
            joinedload(ChangeControl.requester),
            joinedload(ChangeControl.related_document)
        ).filter(
            ChangeControl.id == change_control_id,
            ChangeControl.reviewer_id == reviewer_id,
            ChangeControl.deleted_at.is_(None)
        ).first()
        
        if not change_control:
            return None
            
        return {
            "id": change_control.id,
            "title": change_control.title,
            "change_type": change_control.change_type.value if change_control.change_type else None,
            "description": change_control.description,
            "related_document": f"{change_control.related_document.title} (DOC-{change_control.related_document.id})" if change_control.related_document else None,
            "related_document_id": change_control.related_document_id,
            "requester_name": change_control.requester.full_name if change_control.requester else None,
            "status": change_control.status.value if change_control.status else None
        }
        
    finally:
        session.close()


def get_change_control_for_approval(change_control_id: int, approver_id: int) -> Optional[Dict[str, Any]]:
    """Get change control details for approval with all necessary information"""
    session = SessionLocal()
    try:
        change_control = session.query(ChangeControl).options(
            joinedload(ChangeControl.requester),
            joinedload(ChangeControl.reviewer),
            joinedload(ChangeControl.related_document)
        ).filter(
            ChangeControl.id == change_control_id,
            ChangeControl.approver_id == approver_id,
            ChangeControl.status == ChangeStatusEnum.reviewed,
            ChangeControl.deleted_at.is_(None)
        ).first()
        
        if not change_control:
            return None
            
        return {
            "id": change_control.id,
            "title": change_control.title,
            "change_type": change_control.change_type.value if change_control.change_type else None,
            "description": change_control.description,
            "related_document": f"{change_control.related_document.title} (DOC-{change_control.related_document.id})" if change_control.related_document else None,
            "related_document_id": change_control.related_document_id,
            "requester_name": change_control.requester.full_name if change_control.requester else None,
            "reviewer_name": change_control.reviewer.full_name if change_control.reviewer else None,
            "review_comments": change_control.review_comments,
            "status": change_control.status.value if change_control.status else None
        }
        
    finally:
        session.close()


def get_change_control_dashboard_metrics() -> Dict[str, Any]:
    """Get dashboard metrics for change control requests"""
    session = SessionLocal()
    try:
        # Total Requests (all change controls)
        total_requests = session.query(ChangeControl).filter(
            ChangeControl.deleted_at.is_(None)
        ).count()
        
        # Pending Review (status = submitted)
        pending_review = session.query(ChangeControl).filter(
            ChangeControl.deleted_at.is_(None),
            ChangeControl.status == ChangeStatusEnum.submitted
        ).count()
        
        # Pending Approval (status = reviewed)
        pending_approval = session.query(ChangeControl).filter(
            ChangeControl.deleted_at.is_(None),
            ChangeControl.status == ChangeStatusEnum.reviewed
        ).count()
        
        # Approved (status = approved)
        approved = session.query(ChangeControl).filter(
            ChangeControl.deleted_at.is_(None),
            ChangeControl.status == ChangeStatusEnum.approved
        ).count()
        
        return {
            "total_requests": total_requests,
            "pending_review": pending_review,
            "pending_approval": pending_approval,
            "approved": approved
        }
        
    finally:
        session.close()
