import os
import uuid
import datetime
import base64
from fastapi import UploadFile, HTTPException
from db.database import SessionLocal
from models import Document, Employee, DocumentStatusEnum, DocumentReview, DocumentView, Role
from schemas import DocumentTypeEnum
from schemas import DocumentCreateSchema
from models import Role

UPLOAD_DIR = "uploads/documents"

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

def update_document_version(document: Document, new_status: DocumentStatusEnum) -> str:
    """
    Update document version based on status change
    - draft: 1.0
    - under_review: 1.1
    - approved: 1.2
    - rejected: 2.0 (major version increment)
    """
    current_version = document.version
    
    if new_status == DocumentStatusEnum.draft:
        # If coming from rejected, increment major version
        if document.status == DocumentStatusEnum.rejected:
            major, minor = map(int, current_version.split('.'))
            new_version = f"{major + 1}.0"
        else:
            new_version = "1.0"
    elif new_status == DocumentStatusEnum.under_review:
        new_version = "1.1"
    elif new_status == DocumentStatusEnum.under_approval:
        new_version = "1.1"  # Keep same version when going to approval
    elif new_status == DocumentStatusEnum.approved:
        new_version = "1.2"
    elif new_status == DocumentStatusEnum.rejected:
        # Increment major version for rejection
        major, minor = map(int, current_version.split('.'))
        new_version = f"{major + 1}.0"
    else:
        new_version = current_version  # Keep current version for other statuses
    
    document.version = new_version
    return new_version

def save_uploaded_file(file: UploadFile) -> tuple[str, str, int, str]:
    """Save uploaded file and return (file_path, file_name, file_size, file_base64)"""
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Read file content
    content = file.file.read()
    file_size = len(content)
    
    # Convert to base64
    file_base64 = base64.b64encode(content).decode('utf-8')
    
    # Save file (optional - for backward compatibility)
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    return file_path, file.filename, file_size, file_base64

def add_document_to_db(document_data: DocumentCreateSchema, file_path: str, file_name: str, file_size: int, file_base64: str, uploaded_by: int):
    session = SessionLocal()
    try:
        document = Document(
            title=document_data.title,
            document_type=document_data.document_type.value,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            file_base64=file_base64,
            content=document_data.content,
            uploaded_by=uploaded_by,
            status=DocumentStatusEnum.draft,
            version="1.0"  # Initial version for draft status
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        return document
    finally:
        session.close()

def get_documents_from_db(status: str = None, document_type: str = None, search: str = None):
    session = SessionLocal()
    try:
        from sqlalchemy.orm import joinedload
        
        query = session.query(Document).filter(Document.deleted_at.is_(None))
        
        # Use eager loading to load relationships
        query = query.options(
            joinedload(Document.uploader),
            joinedload(Document.assigned_approver),
            joinedload(Document.approver)
        )
        
        if status:
            # Convert string to enum for comparison
            try:
                status_enum = DocumentStatusEnum(status)
                query = query.filter(Document.status == status_enum)
            except ValueError:
                # If status is not a valid enum value, return empty result
                return []
        if document_type:
            # Convert string to enum for comparison
            try:
                doc_type_enum = DocumentTypeEnum.from_string(document_type)
                query = query.filter(Document.document_type == doc_type_enum)
            except ValueError:
                # If document_type is not a valid enum value, return empty result
                return []
        if search:
            query = query.filter(Document.title.ilike(f"%{search}%"))
        
        return query.order_by(Document.created_at.desc()).all()
    finally:
        session.close()

def get_document_by_id(document_id: int):
    session = SessionLocal()
    try:
        from sqlalchemy.orm import joinedload
        
        query = session.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None))
        
        # Use eager loading to load relationships
        query = query.options(
            joinedload(Document.uploader),
            joinedload(Document.assigned_approver),
            joinedload(Document.approver)
        )
        
        return query.first()
    finally:
        session.close()

def delete_document_from_db(document_id: int):
    session = SessionLocal()
    try:
        document = session.query(Document).filter(Document.id == document_id).first()
        if not document:
            return False
        
        # Soft delete
        document.deleted_at = datetime.datetime.utcnow()
        session.commit()
        
        # Delete physical file
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        return True
    finally:
        session.close()

def get_document_statistics():
    session = SessionLocal()
    try:
        total_documents = session.query(Document).filter(Document.deleted_at.is_(None)).count()
        draft_documents = session.query(Document).filter(Document.status == DocumentStatusEnum.draft, Document.deleted_at.is_(None)).count()
        approved_documents = session.query(Document).filter(Document.status == DocumentStatusEnum.approved, Document.deleted_at.is_(None)).count()
        under_review_documents = session.query(Document).filter(Document.status == DocumentStatusEnum.under_review, Document.deleted_at.is_(None)).count()
        under_approval_documents = session.query(Document).filter(Document.status == DocumentStatusEnum.under_approval, Document.deleted_at.is_(None)).count()
        
        return {
            "total_documents": total_documents,
            "draft_documents": draft_documents,
            "approved_documents": approved_documents,
            "under_review_documents": under_review_documents,
            "under_approval_documents": under_approval_documents
        }
    finally:
        session.close()

def send_document_to_reviewer(document_id: int, signature: str, reviewer_id: int = None):
    session = SessionLocal()
    try:
        document = session.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
        if not document:
            return None, "Document not found"
        
        if document.status != DocumentStatusEnum.draft:
            return None, f"Document must be in draft status. Current status: {document.status}"
        
        # Update document status to under_review and version to 1.1
        document.status = DocumentStatusEnum.under_review
        document.version = "1.1"
        document.updated_at = datetime.datetime.utcnow()
        
        # Create review record
        review = DocumentReview(
            document_id=document_id,
            reviewer_id=reviewer_id,
            action="sent_to_reviewer",
            signature=signature
        )
        session.add(review)
        
        session.commit()
        session.refresh(document)
        return document, "Document sent to reviewer successfully (Version: 1.1)"
    finally:
        session.close()

def review_document_action(document_id: int, reviewer_id: int, action: str, signature: str, comments: str = None):
    session = SessionLocal()
    try:
        document = session.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
        if not document:
            return None, "Document not found"
        
        if document.status != DocumentStatusEnum.under_review:
            return None, f"Document must be under review. Current status: {document.status}"
        
        # Create review record
        review = DocumentReview(
            document_id=document_id,
            reviewer_id=reviewer_id,
            action=action,
            signature=signature,
            comments=comments
        )
        session.add(review)
        
        # Update document status and version based on action
        if action == "reject":
            document.status = DocumentStatusEnum.rejected
            # Increment major version for rejection
            major, minor = map(int, document.version.split('.'))
            document.version = f"{major + 1}.0"
            message = f"Document rejected and version updated to {document.version}"
        elif action == "review":
            # Keep document under review - approver will be assigned separately
            document.status = DocumentStatusEnum.under_review
            document.version = "1.1"
            message = "Document reviewed successfully (Version: 1.1) - ready for approval assignment"
        
        document.updated_at = datetime.datetime.utcnow()
        
        session.commit()
        session.refresh(document)
        
        return document, message
        
    finally:
        session.close()

def approve_document(document_id: int, signature: str, approved: bool, reviewer_id: int, comments: str = None):
    session = SessionLocal()
    try:
        document = session.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
        if not document:
            return None, "Document not found"
        
        if document.status != DocumentStatusEnum.under_approval:
            return None, f"Document must be under approval. Current status: {document.status}"
        
        # Create review record for approval action
        review = DocumentReview(
            document_id=document_id,
            reviewer_id=reviewer_id,  # Get from auth context
            action="approve" if approved else "reject",
            signature=signature,
            comments=comments
        )
        session.add(review)
        
        # Update document status and version based on approval decision
        if approved:
            document.status = DocumentStatusEnum.approved
            document.version = "1.2"
            document.approved_at = datetime.datetime.utcnow()
            message = "Document approved successfully (Version: 1.2)"
        else:
            document.status = DocumentStatusEnum.rejected
            # Increment major version for rejection
            major, minor = map(int, document.version.split('.'))
            document.version = f"{major + 1}.0"
            message = f"Document rejected and version updated to {document.version}"
        
        document.updated_at = datetime.datetime.utcnow()
        
        session.commit()
        session.refresh(document)
        
        return document, message
    finally:
        session.close()

def get_document_review_history(document_id: int):
    """Get review history for a document"""
    session = SessionLocal()
    try:
        from sqlalchemy.orm import joinedload
        
        reviews = session.query(DocumentReview).filter(
            DocumentReview.document_id == document_id
        ).options(
            joinedload(DocumentReview.reviewer)
        ).order_by(DocumentReview.created_at.desc()).all()
        
        return reviews
    finally:
        session.close()

def get_document_traceability(document_id: int):
    """Get document traceability information"""
    session = SessionLocal()
    try:
        document = session.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()
        
        if not document:
            return None
        
        # Get review history
        reviews = get_document_review_history(document_id)
        
        # Format review history
        review_history = []
        for review in reviews:
            review_history.append({
                "id": review.id,
                "document_id": review.document_id,
                "reviewer_id": review.reviewer_id,
                "reviewer_name": review.reviewer.full_name if review.reviewer else None,
                "action": review.action,
                "signature": review.signature,
                "comments": review.comments,
                "created_at": review.created_at.isoformat() if review.created_at else None
            })
        
        # Get last action
        last_action = None
        last_action_date = None
        if review_history:
            last_action = review_history[0]["action"]
            last_action_date = review_history[0]["created_at"]
        
        return {
            "document_id": document_id,
            "current_status": document.status.value if hasattr(document.status, 'value') else str(document.status),
            "review_history": review_history,
            "total_reviews": len(review_history),
            "last_action": last_action,
            "last_action_date": last_action_date
        }
    finally:
        session.close()

def format_file_size(file_size_bytes: int) -> str:
    """Format file size in human readable format"""
    if file_size_bytes < 1024:
        return f"{file_size_bytes} B"
    elif file_size_bytes < 1024 * 1024:
        return f"{file_size_bytes // 1024} KB"
    elif file_size_bytes < 1024 * 1024 * 1024:
        return f"{file_size_bytes // (1024 * 1024)} MB"
    else:
        return f"{file_size_bytes // (1024 * 1024 * 1024)} GB"

def get_document_preview_data(document_id: int):
    """Get comprehensive document preview data"""
    session = SessionLocal()
    try:
        from sqlalchemy.orm import joinedload
        
        document = session.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).options(
            joinedload(Document.uploader),
            joinedload(Document.approver)
        ).first()
        
        if not document:
            return None
        
        # Generate document number (DOC-{year}{month}{day}-{document_id})
        import time
        from datetime import datetime
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        document_number = f"DOC-{date_str}{str(document.id).zfill(6)}"
        
        # Format file size
        file_size_formatted = format_file_size(document.file_size) if document.file_size else "0 B"
        
        # Format created date
        created_date = document.created_at.strftime("%m/%d/%Y") if document.created_at else ""
        
        return {
            "document_id": document.id,
            "title": document.title,
            "document_number": document_number,
            "document_type": document.document_type,
            "file_name": document.file_name,
            "file_size": document.file_size or 0,
            "file_size_formatted": file_size_formatted,
            "created_date": created_date,
            "status": document.status.value if hasattr(document.status, 'value') else str(document.status),
            "content": document.content,
            "file_path": document.file_path,
            "uploaded_by": document.uploaded_by,
            "uploader_name": document.uploader.full_name if document.uploader else None,
            "approved_by": document.approved_by,
            "approver_name": document.approver.full_name if document.approver else None,
            "approved_at": document.approved_at.isoformat() if document.approved_at else None,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None,
            "version": document.version
        }
    finally:
        session.close()

def check_user_permissions(user_id: int, document_id: int):
    """Check what actions the user can perform on the document"""
    session = SessionLocal()
    try:
        # Get user and their role
        user = session.query(Employee).filter(Employee.id == user_id).first()
        if not user:
            return {
                "can_edit": False,
                "can_review": False,
                "can_approve": False,
                "can_delete": False,
                "current_user_role": "Unknown"
            }
        
        # Get user's role
        role = session.query(Role).filter(Role.id == user.role_id).first()
        role_name = role.name if role else "Unknown"
        
        # Get document
        document = session.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()
        
        if not document:
            return {
                "can_edit": False,
                "can_review": False,
                "can_approve": False,
                "can_delete": False,
                "current_user_role": role_name
            }
        
        # Define permissions based on role and document status
        can_edit = False
        can_review = False
        can_approve = False
        can_delete = False
        
        if role_name == "Admin":
            can_edit = document.status == DocumentStatusEnum.draft
            can_review = True
            can_approve = True
            can_delete = document.status == DocumentStatusEnum.draft
        elif role_name == "Reviewer":
            can_review = document.status == DocumentStatusEnum.under_review
        elif role_name == "Approver":
            can_approve = document.status == DocumentStatusEnum.under_approval
        
        return {
            "can_edit": can_edit,
            "can_review": can_review,
            "can_approve": can_approve,
            "can_delete": can_delete,
            "current_user_role": role_name
        }
    finally:
        session.close()

def add_document_comment(document_id: int, user_id: int, comment: str):
    """Add a comment to a document"""
    session = SessionLocal()
    try:
        # Check if document exists
        document = session.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()
        
        if not document:
            return None, "Document not found"
        
        # Create comment record (assuming you have a DocumentComment model)
        # For now, we'll use the DocumentReview table to store comments
        review = DocumentReview(
            document_id=document_id,
            reviewer_id=user_id,
            action="comment",
            comments=comment
        )
        session.add(review)
        session.commit()
        session.refresh(review)
        
        return review, "Comment added successfully"
    finally:
        session.close()

def get_document_comments(document_id: int):
    """Get all comments for a document"""
    session = SessionLocal()
    try:
        from sqlalchemy.orm import joinedload
        
        # Get comments from DocumentReview table where action is "comment"
        comments = session.query(DocumentReview).filter(
            DocumentReview.document_id == document_id,
            DocumentReview.action == "comment"
        ).options(
            joinedload(DocumentReview.reviewer)
        ).order_by(DocumentReview.created_at.desc()).all()
        
        # Format comments
        formatted_comments = []
        for comment in comments:
            formatted_comments.append({
                "id": comment.id,
                "document_id": comment.document_id,
                "user_id": comment.reviewer_id,
                "user_name": comment.reviewer.full_name if comment.reviewer else "Unknown User",
                "comment": comment.comments,
                "created_at": comment.created_at.isoformat() if comment.created_at else None
            })
        
        return formatted_comments
    finally:
        session.close()

def resubmit_rejected_document(document_id: int, uploaded_by: int):
    """
    Resubmit a rejected document - resets to draft status with version 1.0
    """
    session = SessionLocal()
    try:
        document = session.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
        if not document:
            return None, "Document not found"
        
        if document.status != DocumentStatusEnum.rejected:
            return None, f"Document must be in rejected status. Current status: {document.status}"
        
        # Reset to draft status and version 1.0
        document.status = DocumentStatusEnum.draft
        document.version = "1.0"
        document.updated_at = datetime.datetime.utcnow()
        
        # Create review record for resubmission
        review = DocumentReview(
            document_id=document_id,
            reviewer_id=uploaded_by,
            action="resubmitted",
            signature="",
            comments="Document resubmitted after rejection"
        )
        session.add(review)
        
        session.commit()
        session.refresh(document)
        return document, "Document resubmitted successfully (Version: 1.0)"
    finally:
        session.close()

def send_document_to_approver(document_id: int, signature: str, approver_id: int):
    """
    Send document to a specific approver - sets assigned_approver_id and status to under_approval
    """
    session = SessionLocal()
    try:
        document = session.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
        if not document:
            return None, "Document not found"
        
        if document.status != DocumentStatusEnum.under_review:
            return None, f"Document must be under review. Current status: {document.status}"
        
        # Update document status to under_approval and assign approver
        document.status = DocumentStatusEnum.under_approval
        document.assigned_approver_id = approver_id
        document.version = "1.1"  # Keep version 1.1 when going to approval
        document.updated_at = datetime.datetime.utcnow()
        
        # Create review record
        review = DocumentReview(
            document_id=document_id,
            reviewer_id=approver_id,  # Use approver_id as reviewer_id for tracking
            action="sent_to_approver",
            signature=signature
        )
        session.add(review)
        
        session.commit()
        session.refresh(document)
        return document, "Document sent to approver successfully (Version: 1.1)"
    finally:
        session.close()

def track_document_view(document_id: int, viewer_id: int):
    """
    Track when someone views a document - record viewer name and role
    """
    session = SessionLocal()
    try:
        # Get viewer information
        viewer = session.query(Employee).filter(Employee.id == viewer_id).first()
        if not viewer:
            return False, "Viewer not found"
        
        # Get viewer's role
        role = session.query(Role).filter(Role.id == viewer.role_id).first()
        role_name = role.name if role else "Unknown"
        
        # Check if this view already exists (to avoid duplicates in same session)
        existing_view = session.query(DocumentView).filter(
            DocumentView.document_id == document_id,
            DocumentView.viewer_id == viewer_id
        ).order_by(DocumentView.viewed_at.desc()).first()
        
        # Only create new view if last view was more than 5 minutes ago
        if existing_view:
            time_diff = datetime.datetime.utcnow() - existing_view.viewed_at
            if time_diff.total_seconds() < 300:  # 5 minutes
                return True, "View already tracked recently"
        
        # Create new view record
        view = DocumentView(
            document_id=document_id,
            viewer_id=viewer_id,
            viewer_name=viewer.full_name,
            viewer_role=role_name
        )
        session.add(view)
        session.commit()
        
        return True, "View tracked successfully"
    except Exception as e:
        session.rollback()
        return False, f"Error tracking view: {str(e)}"
    finally:
        session.close()

def get_document_view_history(document_id: int):
    """
    Get document view history with viewer names and roles
    """
    session = SessionLocal()
    try:
        views = session.query(DocumentView).filter(
            DocumentView.document_id == document_id
        ).order_by(DocumentView.viewed_at.desc()).all()
        
        view_history = []
        for view in views:
            view_history.append({
                "id": view.id,
                "viewer_id": view.viewer_id,
                "viewer_name": view.viewer_name,
                "viewer_role": view.viewer_role,
                "viewed_at": view.viewed_at.isoformat() if view.viewed_at else None
            })
        
        return view_history
    finally:
        session.close()

def get_document_view_statistics(document_id: int):
    """
    Get document view statistics
    """
    session = SessionLocal()
    try:
        total_views = session.query(DocumentView).filter(
            DocumentView.document_id == document_id
        ).count()
        
        unique_viewers = session.query(DocumentView.viewer_id).filter(
            DocumentView.document_id == document_id
        ).distinct().count()
        
        # Get views by role
        from sqlalchemy import func
        role_views = session.query(
            DocumentView.viewer_role,
            func.count(DocumentView.id).label('count')
        ).filter(
            DocumentView.document_id == document_id
        ).group_by(DocumentView.viewer_role).all()
        
        role_breakdown = {role: count for role, count in role_views}
        
        return {
            "total_views": total_views,
            "unique_viewers": unique_viewers,
            "views_by_role": role_breakdown
        }
    finally:
        session.close()

def get_available_approvers():
    """
    Get list of available approvers (users with Approver role)
    """
    session = SessionLocal()
    try:
        # Get the Approver role
        approver_role = session.query(Role).filter(Role.name == "Approver").first()
        if not approver_role:
            return []
        
        # Get all employees with Approver role
        approvers = session.query(Employee).filter(
            Employee.role_id == approver_role.id,
            Employee.deleted_at.is_(None)
        ).all()
        
        approver_list = []
        for approver in approvers:
            approver_list.append({
                "id": approver.id,
                "name": approver.full_name,
                "email": approver.email,
                "department": approver.department_obj.name if approver.department_obj else None
            })
        
        return approver_list
    finally:
        session.close()

def fix_document_status(document_id: int):
    """
    Fix document status if it's in under_approval without assigned approver
    """
    session = SessionLocal()
    try:
        document = session.query(Document).filter(Document.id == document_id, Document.deleted_at.is_(None)).first()
        if not document:
            return None, "Document not found"
        
        # If document is under_approval but has no assigned approver, fix it
        if document.status == DocumentStatusEnum.under_approval and document.assigned_approver_id is None:
            document.status = DocumentStatusEnum.under_review
            document.updated_at = datetime.datetime.utcnow()
            session.commit()
            session.refresh(document)
            return document, "Document status fixed - moved back to under_review"
        
        return document, "Document status is correct"
    finally:
        session.close()

def calculate_status_duration(document_id: int):
    """
    Calculate how long the document has been in its current status
    """
    session = SessionLocal()
    try:
        document = session.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()
        
        if not document:
            return None
        
        current_status = document.status.value if hasattr(document.status, 'value') else str(document.status)
        
        # Get the most recent review action that changed the status
        reviews = session.query(DocumentReview).filter(
            DocumentReview.document_id == document_id
        ).order_by(DocumentReview.created_at.desc()).all()
        
        # Determine when the current status started
        status_start_time = None
        
        if reviews:
            # Look for the most recent status change
            for review in reviews:
                if review.action in ['sent_to_reviewer', 'review', 'approve', 'reject', 'sent_to_approver']:
                    # Map actions to statuses
                    action_to_status = {
                        'sent_to_reviewer': 'under_review',
                        'review': 'under_approval',  # After review, goes to approval
                        'sent_to_approver': 'under_approval',
                        'approve': 'approved',
                        'reject': 'rejected'
                    }
                    
                    expected_status = action_to_status.get(review.action)
                    if expected_status == current_status:
                        status_start_time = review.created_at
                        break
        
        # If no review found, use document creation time for draft status
        if not status_start_time:
            status_start_time = document.created_at
        
        # Calculate duration
        if status_start_time:
            now = datetime.datetime.utcnow()
            duration = now - status_start_time
            days = duration.days
            
            # Format duration message
            if days == 0:
                return f"In {current_status.replace('_', ' ')} for less than a day"
            elif days == 1:
                return f"In {current_status.replace('_', ' ')} for 1 day"
            else:
                return f"In {current_status.replace('_', ' ')} for {days} days"
        
        return f"In {current_status.replace('_', ' ')}"
        
    finally:
        session.close()

def get_comprehensive_viewer_info(document_id: int):
    """
    Get simple viewer information - just who viewed the document
    """
    session = SessionLocal()
    try:
        # Get view history
        view_history = get_document_view_history(document_id)
        
        # Get unique viewers only (no duplicates)
        unique_viewers = {}
        
        for view in view_history:
            viewer_id = view["viewer_id"]
            if viewer_id not in unique_viewers:
                # Get viewer's signature from Employee table
                viewer = session.query(Employee).filter(Employee.id == viewer_id).first()
                signature = viewer.signature if viewer and viewer.signature else None
                
                unique_viewers[viewer_id] = {
                    "name": view["viewer_name"],
                    "signature": signature
                }
        
        # Convert to list
        viewers_list = list(unique_viewers.values())
        
        return viewers_list
    finally:
        session.close()


