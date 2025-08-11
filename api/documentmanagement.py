from fastapi import APIRouter, Depends, Query, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import FileResponse
from typing import Optional
import datetime
from schemas import (
    DocumentCreateSchema, DocumentListResponseSchema, DocumentResponseSchema, 
    DocumentTypeEnum, DocumentReviewSchema, DocumentApproverSchema, DocumentReviewActionSchema, 
    DocumentApprovalSchema, DocumentViewResponseSchema, DocumentCommentCreateSchema,
    DocumentCommentListSchema
)
from api.employeemanagement import admin_auth, reviewer_auth, approver_auth, get_current_user
from services.documentservice import (
    save_uploaded_file, 
    add_document_to_db, 
    get_documents_from_db, 
    get_document_by_id,
    delete_document_from_db,
    get_document_statistics,
    send_document_to_reviewer,
    send_document_to_approver,
    review_document_action,
    approve_document,
    get_document_review_history,
    get_document_traceability,
    get_document_preview_data,
    check_user_permissions,
    add_document_comment,
    get_document_comments,
    resubmit_rejected_document,
    track_document_view,
    get_document_view_history,
    get_document_view_statistics,
    get_available_approvers,
    fix_document_status,
    get_comprehensive_viewer_info
)
import os
from db.database import SessionLocal
from models import Employee, Role

router = APIRouter(
    prefix="/document",
    tags=["Document Management"]
)

def document_access_auth(request: Request):
    """Authentication for document access - allows Admin, Approver, and Reviewer roles"""
    employee = get_current_user(request)
    session: SessionLocal = SessionLocal()
    try:
        # Get the required roles
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        approver_role = session.query(Role).filter(Role.name == "Approver").first()
        reviewer_role = session.query(Role).filter(Role.name == "Reviewer").first()
        
        if not admin_role or not approver_role or not reviewer_role:
            raise HTTPException(status_code=403, detail="Required roles not found")
        
        # Check if user has any of the allowed roles
        if (getattr(employee, 'role_id', None) == getattr(admin_role, 'id', None) or
            getattr(employee, 'role_id', None) == getattr(approver_role, 'id', None) or
            getattr(employee, 'role_id', None) == getattr(reviewer_role, 'id', None)):
            return employee
        else:
            raise HTTPException(status_code=403, detail="Access denied. Only Admin, Approver, and Reviewer users can access this resource")
    finally:
        session.close()

@router.post("/upload", summary="Upload document")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_type: str = Form(...),
    content: Optional[str] = Form(None),
    current_user = Depends(document_access_auth)
):
    print(f"DEBUG: Received document_type: '{document_type}'")  # Debug line
    # Validate file type
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Validate file size (max 10MB)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size must be less than 10MB")
    
    # Validate and convert document_type
    try:
        doc_type_enum = DocumentTypeEnum.from_string(document_type)
    except ValueError as e:
        valid_types = [e.value for e in DocumentTypeEnum]
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid document type. Must be one of: {', '.join(valid_types)}"
        )
    
    try:
        # Save file and get base64 content
        file_path, file_name, file_size, file_base64 = save_uploaded_file(file)
        
        # Create document data
        document_data = DocumentCreateSchema(
            title=title,
            document_type=doc_type_enum,
            content=content
        )
        
        # Add to database (uploaded_by will be set from auth context)
        document = add_document_to_db(document_data, file_path, file_name, file_size, file_base64, uploaded_by=current_user.id)
        
        return {"message": "Document uploaded successfully", "document_id": document.id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@router.get("/all", summary="View all documents with base64 content")
def view_all_documents(
    status: str = Query(None, description="Filter by status"),
    document_type: str = Query(None, description="Filter by document type"),
    search: str = Query(None, description="Search by title"),
    current_user = Depends(document_access_auth)
):
    documents = get_documents_from_db(status, document_type, search)
    result = []
    
    for document in documents:
        result.append({
            "id": document.id,
            "title": document.title,
            "document_type": document.document_type,
            "file_name": document.file_name,
            "file_size": document.file_size,
            "file_base64": document.file_base64,  # Include base64 content
            "version": document.version,
            "status": document.status,
            "content": document.content,
            "uploaded_by": document.uploaded_by,
            "uploader_name": document.uploader.full_name if document.uploader else None,
            "approved_by": document.approved_by,
            "approver_name": document.approver.full_name if document.approver else None,
            "approved_at": document.approved_at.isoformat() if document.approved_at else None,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "updated_at": document.updated_at.isoformat() if document.updated_at else None
        })
    
    return {
        "documents": result,
        "total_count": len(result),
        "filtered_by": {
            "status": status,
            "document_type": document_type,
            "search": search
        } if any([status, document_type, search]) else None
    }

@router.get("/types", summary="Get available document types")
def get_document_types(current_user = Depends(document_access_auth)):
    return {
        "document_types": [
            {"value": e.value, "label": e.value} 
            for e in DocumentTypeEnum
        ]
    }

@router.get("/statistics", summary="Get document statistics")
def get_document_stats(current_user = Depends(document_access_auth)):
    return get_document_statistics()

@router.get("/{document_id}", summary="Get document by ID with base64 content and viewer information")
def get_document(document_id: int, current_user = Depends(document_access_auth)):
    """
    Get document with base64 content and viewer tracking information
    """
    document = get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Track document view
    track_document_view(document_id, current_user.id)
    
    # Get simple viewer information
    viewers = get_comprehensive_viewer_info(document_id)
    
    # Get status duration
    from services.documentservice import calculate_status_duration
    status_duration = calculate_status_duration(document_id)
    
    # Prepare document data with base64
    document_data = {
        "id": document.id,
        "title": document.title,
        "document_type": document.document_type,
        "file_name": document.file_name,
        "file_size": document.file_size,
        "file_base64": document.file_base64,  # Include base64 content
        "version": document.version,
        "status": document.status,
        "status_duration": status_duration,
        "content": document.content,
        "uploaded_by": document.uploaded_by,
        "uploader_name": document.uploader.full_name if document.uploader else None,
        "assigned_approver_id": document.assigned_approver_id,
        "assigned_approver_name": document.assigned_approver.full_name if document.assigned_approver else None,
        "approved_by": document.approved_by,
        "approver_name": document.approver.full_name if document.approver else None,
        "approved_at": document.approved_at.isoformat() if document.approved_at else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None
    }
    
    # Get review history
    from services.documentservice import get_document_review_history
    reviews = get_document_review_history(document_id)
    
    # Format review history
    review_history = []
    for review in reviews:
        review_history.append({
            "id": review.id,
            "reviewer_name": review.reviewer.full_name if review.reviewer else None,
            "action": review.action,
            "signature": review.signature,
            "comments": review.comments,
            "created_at": review.created_at.isoformat() if review.created_at else None
        })
    
    return {
        "document": document_data,
        "viewers": viewers,
        "review_history": review_history
    }

@router.get("/{document_id}/view", summary="Get comprehensive document view with traceability and base64 content")
def get_document_view(document_id: int, current_user = Depends(document_access_auth)):
    """
    Get comprehensive document view including:
    - Document preview with metadata and base64 content
    - Traceability and review history
    - User permissions for actions
    """
    # Get document with base64 content
    document = get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Track document view
    track_document_view(document_id, current_user.id)
    
    # Get traceability data
    traceability_data = get_document_traceability(document_id)
    if not traceability_data:
        raise HTTPException(status_code=404, detail="Document traceability not found")
    
    # Check user permissions
    permissions = check_user_permissions(current_user.id, document_id)
    
    # Get status duration
    from services.documentservice import calculate_status_duration
    status_duration = calculate_status_duration(document_id)
    
    # Prepare document data with base64
    document_data = {
        "id": document.id,
        "title": document.title,
        "document_type": document.document_type,
        "file_name": document.file_name,
        "file_size": document.file_size,
        "file_base64": document.file_base64,  # Include base64 content
        "version": document.version,
        "status": document.status,
        "status_duration": status_duration,
        "content": document.content,
        "uploaded_by": document.uploaded_by,
        "uploader_name": document.uploader.full_name if document.uploader else None,
        "assigned_approver_id": document.assigned_approver_id,
        "assigned_approver_name": document.assigned_approver.full_name if document.assigned_approver else None,
        "approved_by": document.approved_by,
        "approver_name": document.approver.full_name if document.approver else None,
        "approved_at": document.approved_at.isoformat() if document.approved_at else None,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None
    }
    
    # Get simple viewer information
    viewers = get_comprehensive_viewer_info(document_id)
    
    # Get review history
    from services.documentservice import get_document_review_history
    reviews = get_document_review_history(document_id)
    
    # Format review history
    review_history = []
    for review in reviews:
        review_history.append({
            "id": review.id,
            "reviewer_name": review.reviewer.full_name if review.reviewer else None,
            "action": review.action,
            "signature": review.signature,
            "comments": review.comments,
            "created_at": review.created_at.isoformat() if review.created_at else None
        })
    
    return {
        "document": document_data,
        "traceability": traceability_data,
        "viewers": viewers,
        "review_history": review_history,
        "can_edit": permissions["can_edit"],
        "can_review": permissions["can_review"],
        "can_approve": permissions["can_approve"],
        "can_delete": permissions["can_delete"],
        "current_user_role": permissions["current_user_role"]
    }



@router.get("/{document_id}/download", summary="Download document")
def download_document(document_id: int, current_user = Depends(document_access_auth)):
    document = get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if we have base64 content
    if document.file_base64:
        import base64
        from fastapi.responses import Response
        
        # Decode base64 content
        pdf_content = base64.b64decode(document.file_base64)
        
        return Response(
            content=pdf_content,
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={document.file_name}"}
        )
    
    # Fallback to file path if base64 is not available
    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    
    return FileResponse(
        path=document.file_path,
        filename=document.file_name,
        media_type='application/pdf'
    )

@router.get("/{document_id}/preview", summary="Preview document PDF in browser")
def preview_document(document_id: int, current_user = Depends(document_access_auth)):
    """
    Return PDF for inline preview in browser
    """
    document = get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if we have base64 content
    if document.file_base64:
        import base64
        from fastapi.responses import Response
        
        # Decode base64 content
        pdf_content = base64.b64decode(document.file_base64)
        
        return Response(
            content=pdf_content,
            media_type='application/pdf',
            headers={"Content-Disposition": "inline"}
        )
    
    # Fallback to file path if base64 is not available
    if not document.file_path or not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="Document file not found")
    
    return FileResponse(
        path=document.file_path,
        filename=document.file_name,
        media_type='application/pdf',
        headers={"Content-Disposition": "inline"}
    )


    
    # HTML template for document viewer
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document Viewer - {document_data['title']}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background-color: #f5f5f5;
                color: #333;
            }}
            
            .document-viewer {{
                display: flex;
                height: 100vh;
            }}
            
            .document-sidebar {{
                width: 350px;
                background: white;
                border-right: 1px solid #e1e5e9;
                display: flex;
                flex-direction: column;
            }}
            
            .document-header {{
                padding: 20px;
                border-bottom: 1px solid #e1e5e9;
            }}
            
            .document-title {{
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 16px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .document-icon {{
                width: 20px;
                height: 20px;
                background: #0066cc;
                border-radius: 4px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }}
            
            .document-meta {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                font-size: 14px;
            }}
            
            .meta-item {{
                display: flex;
                flex-direction: column;
            }}
            
            .meta-label {{
                color: #6b7280;
                font-size: 12px;
                margin-bottom: 2px;
            }}
            
            .meta-value {{
                font-weight: 500;
            }}
            
            .document-preview {{
                flex: 1;
                padding: 16px;
            }}
            
            .preview-header {{
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 16px;
            }}
            
            .preview-title {{
                font-size: 16px;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .preview-icon {{
                width: 16px;
                height: 16px;
                opacity: 0.7;
            }}
            
            .pdf-viewer {{
                width: 100%;
                height: calc(100vh - 120px);
                border: 1px solid #e1e5e9;
                border-radius: 8px;
                background: white;
            }}
            
            .comments-section {{
                border-top: 1px solid #e1e5e9;
                padding: 16px;
                max-height: 300px;
                overflow-y: auto;
            }}
            
            .comments-header {{
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 12px;
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            
            .comment-item {{
                padding: 8px 0;
                border-bottom: 1px solid #f3f4f6;
            }}
            
            .comment-author {{
                font-size: 12px;
                font-weight: 600;
                color: #374151;
            }}
            
            .comment-text {{
                font-size: 12px;
                color: #6b7280;
                margin-top: 4px;
            }}
            
            .comment-date {{
                font-size: 10px;
                color: #9ca3af;
                margin-top: 4px;
            }}
            
            .status-badge {{
                display: inline-block;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
                text-transform: uppercase;
            }}
            
            .status-draft {{
                background: #fef3c7;
                color: #d97706;
            }}
            
            .status-approved {{
                background: #d1fae5;
                color: #065f46;
            }}
            
            .status-under-review {{
                background: #dbeafe;
                color: #1d4ed8;
            }}
            
            .status-under-approval {{
                background: #e0e7ff;
                color: #5b21b6;
            }}
            
            .status-rejected {{
                background: #fee2e2;
                color: #dc2626;
            }}
            
            .close-btn {{
                position: absolute;
                top: 16px;
                right: 16px;
                width: 32px;
                height: 32px;
                border: none;
                background: #f3f4f6;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                font-size: 16px;
                color: #6b7280;
            }}
            
            .close-btn:hover {{
                background: #e5e7eb;
            }}
            
            .action-buttons {{
                padding: 16px;
                border-top: 1px solid #e1e5e9;
                display: flex;
                gap: 8px;
                flex-wrap: wrap;
            }}
            
            .btn {{
                padding: 8px 16px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                background: white;
                color: #374151;
                font-size: 12px;
                font-weight: 500;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                gap: 4px;
            }}
            
            .btn:hover {{
                background: #f9fafb;
            }}
            
            .btn-primary {{
                background: #3b82f6;
                color: white;
                border-color: #3b82f6;
            }}
            
            .btn-primary:hover {{
                background: #2563eb;
            }}
            
            .btn-success {{
                background: #10b981;
                color: white;
                border-color: #10b981;
            }}
            
            .btn-danger {{
                background: #ef4444;
                color: white;
                border-color: #ef4444;
            }}
        </style>
    </head>
    <body>
        <div class="document-viewer">
            <div class="document-sidebar">
                <div class="document-header">
                    <div class="document-title">
                        <div class="document-icon">📄</div>
                        {document_data['title']}
                    </div>
                    
                    <div class="document-meta">
                        <div class="meta-item">
                            <div class="meta-label">Document Number</div>
                            <div class="meta-value">{document_data['document_number']}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Type</div>
                            <div class="meta-value">{document_data['document_type']}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Created</div>
                            <div class="meta-value">{document_data['created_date']}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">File Size</div>
                            <div class="meta-value">{document_data['file_size_formatted']}</div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Status</div>
                            <div class="meta-value">
                                <span class="status-badge status-{document_data['status'].replace('_', '-')}">{document_data['status'].replace('_', ' ').title()}</span>
                            </div>
                        </div>
                        <div class="meta-item">
                            <div class="meta-label">Version</div>
                            <div class="meta-value">{document_data['version']}</div>
                        </div>
                    </div>
                </div>
                
                {"" if not permissions['can_edit'] and not permissions['can_review'] and not permissions['can_approve'] and not permissions['can_delete'] else f'''
                <div class="action-buttons">
                    {f'<a href="/document/{document_id}/download" class="btn btn-primary" target="_blank">📥 Download</a>' if True else ''}
                    {f'<button class="btn" onclick="window.print()">🖨️ Print</button>' if True else ''}
                    {f'<button class="btn btn-success">✓ Review</button>' if permissions['can_review'] else ''}
                    {f'<button class="btn btn-success">✓ Approve</button>' if permissions['can_approve'] else ''}
                    {f'<button class="btn btn-danger">🗑️ Delete</button>' if permissions['can_delete'] else ''}
                </div>
                '''}
                
                <div class="comments-section">
                    <div class="comments-header">
                        💬 Comments
                        <span style="font-size: 12px; color: #6b7280; font-weight: normal;">({len(comments)})</span>
                    </div>
                    {"".join([f'''
                    <div class="comment-item">
                        <div class="comment-author">{comment['user_name']}</div>
                        <div class="comment-text">{comment['comment']}</div>
                        <div class="comment-date">{comment['created_at'][:10] if comment['created_at'] else ''}</div>
                    </div>
                    ''' for comment in comments]) if comments else '<div style="color: #9ca3af; font-size: 12px; text-align: center; padding: 20px;">No comments yet</div>'}
                </div>
            </div>
            
            <div class="document-preview">
                <div class="preview-header">
                    <div class="preview-title">
                        <span class="preview-icon">👁️</span>
                        Document Preview
                    </div>
                    <button class="close-btn" onclick="window.close()" title="Close">✕</button>
                </div>
                
                <iframe 
                    src="/document/{document_id}/preview" 
                    class="pdf-viewer"
                    frameborder="0">
                    Your browser does not support PDF viewing. 
                    <a href="/document/{document_id}/download">Download the PDF</a> to view it.
                </iframe>
            </div>
        </div>
        
        <script>
            // Add keyboard shortcuts
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'Escape') {{
                    window.close();
                }}
                if (e.ctrlKey && e.key === 'd') {{
                    e.preventDefault();
                    window.open('/document/{document_id}/download');
                }}
                if (e.ctrlKey && e.key === 'p') {{
                    e.preventDefault();
                    window.print();
                }}
            }});
            
            // Auto-resize iframe on window resize
            window.addEventListener('resize', function() {{
                const iframe = document.querySelector('.pdf-viewer');
                if (iframe) {{
                    iframe.style.height = (window.innerHeight - 120) + 'px';
                }}
            }});
        </script>
    </body>
    </html>
    """
    


@router.delete("/{document_id}", summary="Delete document")
def delete_document(document_id: int, current_user = Depends(document_access_auth)):
    success = delete_document_from_db(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted successfully"}

@router.post("/send-to-reviewer", summary="Send document to reviewer")
def send_to_reviewer(review_data: DocumentReviewSchema, current_user = Depends(admin_auth)):
    document, message = send_document_to_reviewer(
        document_id=review_data.document_id,
        signature=review_data.signature,
        reviewer_id=review_data.reviewer_id
    )
    
    if not document:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "document_id": document.id,
        "new_status": document.status
    }

@router.post("/send-to-approver", summary="Send document to specific approver by ID")
def send_to_approver(approver_data: DocumentApproverSchema, current_user = Depends(admin_auth)):
    document, message = send_document_to_approver(
        document_id=approver_data.document_id,
        signature=approver_data.signature,
        approver_id=approver_data.approver_id
    )
    
    if not document:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "document_id": document.id,
        "new_status": document.status
    }

@router.post("/review-action", summary="Reviewer action: Review or Reject document")
def reviewer_action(review_action_data: DocumentReviewActionSchema, current_user = Depends(reviewer_auth)):
    # Validate action (case-insensitive)
    action_lower = review_action_data.action.lower()
    if action_lower not in ["review", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'review' or 'reject'")
    
    # Use the lowercase action
    review_action_data.action = action_lower
    
    document, message = review_document_action(
        document_id=review_action_data.document_id,
        reviewer_id=current_user.id,
        action=review_action_data.action,
        signature=review_action_data.signature,
        comments=review_action_data.comments
    )
    
    if not document:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "document_id": document.id,
        "new_status": document.status
    }

@router.post("/approve", summary="Approve or reject document")
def approve_document_endpoint(approval_data: DocumentApprovalSchema, current_user = Depends(approver_auth)):
    document, message = approve_document(
        document_id=approval_data.document_id,
        signature=approval_data.signature,
        approved=approval_data.approved,
        reviewer_id=current_user.id,
        comments=approval_data.comments
    )
    
    if not document:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "document_id": document.id,
        "new_status": document.status
    }

@router.get("/{document_id}/comments", summary="Get document comments", response_model=DocumentCommentListSchema)
def get_document_comments_endpoint(document_id: int, current_user = Depends(document_access_auth)):
    """Get all comments for a document"""
    comments = get_document_comments(document_id)
    
    return {
        "comments": comments,
        "total_count": len(comments)
    }

@router.post("/{document_id}/comments", summary="Add comment to document")
def add_document_comment_endpoint(
    document_id: int, 
    comment_data: DocumentCommentCreateSchema,
    current_user = Depends(document_access_auth)
):
    """Add a comment to a document"""
    result, message = add_document_comment(
        document_id=document_id,
        user_id=current_user.id,
        comment=comment_data.comment
    )
    
    if not result:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "comment_id": result.id
    }

@router.post("/{document_id}/resubmit", summary="Resubmit rejected document")
def resubmit_document_endpoint(document_id: int, current_user = Depends(document_access_auth)):
    """Resubmit a rejected document - resets to draft status with version 1.0"""
    result, message = resubmit_rejected_document(
        document_id=document_id,
        uploaded_by=current_user.id
    )
    
    if not result:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "document_id": result.id,
        "new_status": result.status,
        "new_version": result.version
    }

@router.get("/available-approvers", summary="Get list of available approvers")
def get_available_approvers_endpoint(current_user = Depends(admin_auth)):
    """Get list of all available approvers (users with Approver role)"""
    approvers = get_available_approvers()
    return {
        "approvers": approvers,
        "total_count": len(approvers)
    }

@router.post("/{document_id}/fix-status", summary="Fix document status if needed")
def fix_document_status_endpoint(document_id: int, current_user = Depends(admin_auth)):
    """Fix document status if it's in under_approval without assigned approver"""
    result, message = fix_document_status(document_id)
    
    if not result:
        raise HTTPException(status_code=400, detail=message)
    
    return {
        "message": message,
        "document_id": result.id,
        "new_status": result.status
    }


