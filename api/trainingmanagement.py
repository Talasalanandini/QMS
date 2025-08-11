from fastapi import APIRouter, Depends, Query, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from typing import Optional
import os
import asyncio
from schemas import (
    TrainingCreateSchema, TrainingResponseSchema, TrainingListResponseSchema,
    TrainerResponseSchema, TrainingAssignmentCreateSchema, TrainingAssignmentListResponseSchema,
    EmployeeListForAssignmentSchema, TrainingCreateWithFileSchema,
    AssessmentQuestionCreateSchema, AssessmentQuestionResponseSchema, DifficultyLevelEnum,
    TrainingAssignmentModalSchema, UserForAssignmentSchema, UserAssignmentListSchema
)
from api.employeemanagement import admin_auth
from api.documentmanagement import document_access_auth
from services.trainingservice import (
    add_training_to_db, add_training_with_file_to_db, get_trainings_from_db, get_training_by_id,
    delete_training_from_db, get_training_statistics, get_trainers_by_department,
    get_training_types, get_departments, save_training_file
)
from services.trainingassignmentservice import (
    assign_trainings_to_employees, get_employees_for_assignment,
    get_training_assignments as get_training_assignments_service, update_assignment_status, get_assignment_statistics
)
from db.database import SessionLocal
from models import AssessmentQuestion, DifficultyLevelEnum as ModelDifficultyLevelEnum

router = APIRouter(
    prefix="/training",
    tags=["Training Management"]
)

@router.post("/create-with-file", summary="Create new training with file upload")
async def create_training_with_file(
    request: Request,
    current_user = Depends(admin_auth)
):
    """
    Create a new training course with file upload
    
    **Parameters:**
    - title (required): Course title
    - course_code (required): Course code (e.g., TRN-001)
    - description (optional): Course description
    - trainer_id (required): Trainer ID
    - duration_hours (optional): Duration in hours (default: 8)
    - passing_score (required): Passing score percentage (default: 80)
    - start_date (required): Start date (dd-mm-yyyy format)
    - end_date (required): End date (dd-mm-yyyy format)
    - content_type (required): Content type: 'document' or 'video'
    - approved_document_id (optional): ID of approved document (required when content_type is 'document')
    - mandatory (optional): Whether training is mandatory (default: false)
    - document_file (optional): Document file (PDF, DOC, DOCX, PPT, PPTX - max 50MB)
    - video_file (optional): Video file (MP4, AVI, MOV, WMV, FLV, WebM - max 100MB)
    
    **Rules:**
    - If content_type is 'document': Either provide approved_document_id for existing approved document OR upload document_file
    - If content_type is 'video': Upload video_file (will be converted to base64)
    """
    """Create a new training course with file upload
    
    - If content_type is 'document': Either provide approved_document_id for existing approved document OR upload document_file
    - If content_type is 'video': Upload video_file (will be converted to base64)
    """
    try:
        # Parse form data manually
        form_data = await request.form()
        
        # Extract form fields
        title = form_data.get("title")
        course_code = form_data.get("course_code")
        description = form_data.get("description")
        trainer_id = form_data.get("trainer_id")
        duration_hours = form_data.get("duration_hours")
        passing_score = form_data.get("passing_score")
        start_date = form_data.get("start_date")
        end_date = form_data.get("end_date")
        content_type = form_data.get("content_type")
        approved_document_id = form_data.get("approved_document_id")
        mandatory = form_data.get("mandatory", "false").lower() == "true"
        
        # Get file uploads
        document_file = form_data.get("document_file")
        video_file = form_data.get("video_file")
        
        # Validate required fields
        if not title:
            raise HTTPException(status_code=400, detail="Title is required")
        if not course_code:
            raise HTTPException(status_code=400, detail="Course code is required")
        if not trainer_id:
            raise HTTPException(status_code=400, detail="Trainer ID is required")
        if not passing_score:
            raise HTTPException(status_code=400, detail="Passing score is required")
        if not start_date:
            raise HTTPException(status_code=400, detail="Start date is required")
        if not end_date:
            raise HTTPException(status_code=400, detail="End date is required")
        if not content_type:
            raise HTTPException(status_code=400, detail="Content type is required")
        
        # Convert types
        try:
            trainer_id = int(trainer_id)
            passing_score = int(passing_score)
            duration_hours = int(duration_hours) if duration_hours else None
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid numeric values")
        
        # Validate content_type
        if content_type not in ["document", "video"]:
            raise HTTPException(status_code=400, detail="Content type must be 'document' or 'video'")
        
        # Handle approved_document_id - convert empty string to None
        approved_doc_id = None
        if approved_document_id and approved_document_id.strip():
            try:
                approved_doc_id = int(approved_document_id)
            except ValueError:
                raise HTTPException(status_code=400, detail="approved_document_id must be a valid integer")
        
        # Handle file upload based on content_type
        file_path = None
        file_name = None
        file_size = None
        file_type = None
        file_base64 = None
        
        # Add timeout warning for large files
        print("Starting file processing...")
        
        if content_type == "document":
            if approved_doc_id:
                # Use existing approved document
                from services.documentservice import get_document_by_id
                document = get_document_by_id(approved_doc_id)
                if not document:
                    raise HTTPException(status_code=400, detail="Approved document not found")
                if document.status != "approved":
                    raise HTTPException(status_code=400, detail="Document must be approved")
                file_path = document.file_path
                file_name = document.file_name
                file_size = document.file_size
                file_type = os.path.splitext(document.file_name)[1] if document.file_name else None
                
                # Generate base64 for approved document (only for smaller files to avoid timeout)
                if file_path and os.path.exists(file_path):
                    try:
                        file_size_bytes = os.path.getsize(file_path)
                        # Only encode files smaller than 10MB to avoid timeout
                        if file_size_bytes <= 10 * 1024 * 1024:  # 10MB limit
                            with open(file_path, 'rb') as f:
                                content = f.read()
                                import base64
                                file_base64 = base64.b64encode(content).decode('utf-8')
                        else:
                            print(f"Warning: File too large for base64 encoding ({file_size_bytes} bytes). Skipping base64 generation.")
                            file_base64 = None
                    except Exception as e:
                        print(f"Warning: Could not generate base64 for approved document: {e}")
                        file_base64 = None
                else:
                    file_base64 = None
            else:
                # Upload new document file
                if not document_file or not hasattr(document_file, 'filename') or not document_file.filename:
                    raise HTTPException(status_code=400, detail="Document file is required when content_type is 'document' and no approved_document_id provided")
                
                # Validate file type
                if not document_file.filename.lower().endswith(('.pdf', '.doc', '.docx', '.ppt', '.pptx')):
                    raise HTTPException(status_code=400, detail="Document files must be PDF, DOC, DOCX, PPT, or PPTX")
                
                # Validate file size (max 50MB for documents)
                if document_file.size and document_file.size > 50 * 1024 * 1024:
                    raise HTTPException(status_code=400, detail="Document file size must be less than 50MB")
                
                # Save file
                file_path, file_name, file_size, file_type, file_base64 = save_training_file(document_file)
                
        elif content_type == "video":
            # Upload video file
            if not video_file or not hasattr(video_file, 'filename') or not video_file.filename:
                raise HTTPException(status_code=400, detail="Video file is required when content_type is 'video'")
            
            # Validate file type
            if not video_file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm')):
                raise HTTPException(status_code=400, detail="Video files must be MP4, AVI, MOV, WMV, FLV, or WebM")
            
            # Validate file size (max 100MB for videos)
            if video_file.size and video_file.size > 100 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Video file size must be less than 100MB")
            
            # Save file
            file_path, file_name, file_size, file_type, file_base64 = save_training_file(video_file)
        
        # Convert date format from dd-mm-yyyy to yyyy-mm-dd (ISO format)
        def convert_date_format(date_str):
            if not date_str:
                return None
            try:
                # Parse dd-mm-yyyy format
                from datetime import datetime
                date_obj = datetime.strptime(date_str, "%d-%m-%Y")
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                # If it's already in ISO format, return as is
                try:
                    datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    return date_str
                except ValueError:
                    raise HTTPException(status_code=400, detail=f"Invalid date format: {date_str}. Use dd-mm-yyyy format (e.g., 01-01-2024)")
        
        # Convert dates
        iso_start_date = convert_date_format(start_date)
        iso_end_date = convert_date_format(end_date)
        
        # Create training data
        training_data = TrainingCreateWithFileSchema(
            title=title,
            course_code=course_code,
            description=description,
            trainer_id=trainer_id,
            duration_hours=duration_hours,
            passing_score=passing_score,
            start_date=iso_start_date,
            end_date=iso_end_date,
            content_type=content_type,
            approved_document_id=approved_doc_id,
            mandatory=mandatory,
            file_path=file_path,
            file_name=file_name,
            file_size=file_size,
            file_type=file_type,
            file_base64=file_base64
        )
        
        # Add to database
        training = add_training_with_file_to_db(training_data, created_by=current_user.id)
        
        return {
            "message": "Training created successfully",
            "training_id": training.id,
            "course_code": course_code,
            "file_name": file_name,
            "file_size": file_size,
            "content_type": content_type,
            "file_base64": file_base64
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create training: {str(e)}")

@router.get("/all", summary="Get all trainings with search")
async def get_all_trainings(
    search: Optional[str] = Query(None, description="Search by title, description, or course code"),
    current_user = Depends(admin_auth)
):
    """Get all trainings with search capabilities"""
    try:
        trainings = get_trainings_from_db(
            search=search
        )
        
        # Convert to response schema
        training_responses = []
        for training in trainings:
            response = TrainingResponseSchema(
                id=training.id,
                title=training.title,
                course_code=training.course_code,
                description=training.description,
                trainer_id=training.trainer_id,
                trainer_name=training.trainer.full_name if training.trainer else None,
                trainer_email=training.trainer.email if training.trainer else None,
                duration_hours=training.duration_hours,
                passing_score=training.passing_score,
                start_date=training.start_date.isoformat() if training.start_date else None,
                end_date=training.end_date.isoformat() if training.end_date else None,
                mandatory=training.mandatory,
                status=training.status.value if training.status else None,
                created_by=training.created_by,
                creator_name=training.creator.full_name if training.creator else None,
                created_at=training.created_at.isoformat() if training.created_at else None,
                updated_at=training.updated_at.isoformat() if training.updated_at else None,
                content_type=training.content_type,
                file_name=training.file_name,
                file_size=training.file_size,
                file_type=training.file_type
            )
            training_responses.append(response)
        
        return training_responses
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trainings: {str(e)}")

@router.get("/{training_id}", summary="Get single training by ID")
async def get_training(
    training_id: int,
    current_user = Depends(admin_auth)
):
    """Get a single training by its ID"""
    try:
        training = get_training_by_id(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")
        
        response = TrainingResponseSchema(
            id=training.id,
            title=training.title,
            course_code=training.course_code,
            description=training.description,
            trainer_id=training.trainer_id,
            trainer_name=training.trainer.full_name if training.trainer else None,
            trainer_email=training.trainer.email if training.trainer else None,
            duration_hours=training.duration_hours,
            passing_score=training.passing_score,
            start_date=training.start_date.isoformat() if training.start_date else None,
            end_date=training.end_date.isoformat() if training.end_date else None,
            mandatory=training.mandatory,
            status=training.status.value if training.status else None,
            created_by=training.created_by,
            creator_name=training.creator.full_name if training.creator else None,
            created_at=training.created_at.isoformat() if training.created_at else None,
            updated_at=training.updated_at.isoformat() if training.updated_at else None,
            content_type=training.content_type,
            file_name=training.file_name,
            file_size=training.file_size,
            file_type=training.file_type
        )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch training: {str(e)}")

@router.delete("/{training_id}", summary="Delete training by ID")
async def delete_training(
    training_id: int,
    current_user = Depends(admin_auth)
):
    """Soft delete a training by its ID"""
    try:
        success = delete_training_from_db(training_id)
        if not success:
            raise HTTPException(status_code=404, detail="Training not found")
        
        return {"message": "Training deleted successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete training: {str(e)}")

@router.get("/statistics/overview", summary="Get training statistics")
async def get_training_overview_statistics(
    current_user = Depends(admin_auth)
):
    """Get overview statistics for trainings"""
    try:
        stats = get_training_statistics()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {str(e)}")

@router.get("/{training_id}/download", summary="Download training file")
async def download_training_file(
    training_id: int,
    current_user = Depends(admin_auth)
):
    """Download the training file (document or video)"""
    try:
        training = get_training_by_id(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")
        
        if not training.file_path or not training.file_name:
            raise HTTPException(status_code=404, detail="No file associated with this training")
        
        # Check if file exists
        if not os.path.exists(training.file_path):
            raise HTTPException(status_code=404, detail="Training file not found on server")
        
        # Determine content type based on file extension
        content_type = "application/octet-stream"  # Default
        if training.file_type:
            if training.file_type.lower() in ['.pdf']:
                content_type = "application/pdf"
            elif training.file_type.lower() in ['.doc', '.docx']:
                content_type = "application/msword"
            elif training.file_type.lower() in ['.ppt', '.pptx']:
                content_type = "application/vnd.ms-powerpoint"
            elif training.file_type.lower() in ['.mp4']:
                content_type = "video/mp4"
            elif training.file_type.lower() in ['.avi']:
                content_type = "video/x-msvideo"
            elif training.file_type.lower() in ['.mov']:
                content_type = "video/quicktime"
        
        return FileResponse(
            path=training.file_path,
            filename=training.file_name,
            media_type=content_type
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")

# Assessment Question APIs
@router.post("/{training_id}/assessment/question", summary="Create assessment question", response_model=AssessmentQuestionResponseSchema)
async def create_assessment_question(
    training_id: int,
    question: AssessmentQuestionCreateSchema,
    current_user = Depends(admin_auth)
):
    session = SessionLocal()
    try:
        # Validate training_id matches
        if question.training_id != training_id:
            raise HTTPException(status_code=400, detail="training_id mismatch")
        db_question = AssessmentQuestion(
            training_id=training_id,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            correct_option=question.correct_option,
            difficulty_level=ModelDifficultyLevelEnum(question.difficulty_level)
        )
        session.add(db_question)
        session.commit()
        session.refresh(db_question)
        
        # Convert datetime objects to strings for response
        return AssessmentQuestionResponseSchema(
            id=db_question.id,
            training_id=db_question.training_id,
            question_text=db_question.question_text,
            option_a=db_question.option_a,
            option_b=db_question.option_b,
            option_c=db_question.option_c,
            option_d=db_question.option_d,
            correct_option=db_question.correct_option,
            difficulty_level=db_question.difficulty_level.value if db_question.difficulty_level else None,
            created_at=db_question.created_at.isoformat() if db_question.created_at else None,
            updated_at=db_question.updated_at.isoformat() if db_question.updated_at else None
        )
    finally:
        session.close()

@router.get("/{training_id}/assessment/questions", summary="List assessment questions", response_model=list[AssessmentQuestionResponseSchema])
async def list_assessment_questions(
    training_id: int,
    current_user = Depends(admin_auth)
):
    session = SessionLocal()
    try:
        questions = session.query(AssessmentQuestion).filter(
            AssessmentQuestion.training_id == training_id,
            AssessmentQuestion.deleted_at.is_(None)
        ).order_by(AssessmentQuestion.created_at.asc()).all()
        
        # Convert to response schema
        return [
            AssessmentQuestionResponseSchema(
                id=q.id,
                training_id=q.training_id,
                question_text=q.question_text,
                option_a=q.option_a,
                option_b=q.option_b,
                option_c=q.option_c,
                option_d=q.option_d,
                correct_option=q.correct_option,
                difficulty_level=q.difficulty_level.value if q.difficulty_level else None,
                created_at=q.created_at.isoformat() if q.created_at else None,
                updated_at=q.updated_at.isoformat() if q.updated_at else None
            ) for q in questions
        ]
    finally:
        session.close()

@router.get("/{training_id}/assessment/question/{question_id}", summary="Get assessment question", response_model=AssessmentQuestionResponseSchema)
async def get_assessment_question(
    training_id: int,
    question_id: int,
    current_user = Depends(admin_auth)
):
    session = SessionLocal()
    try:
        question = session.query(AssessmentQuestion).filter(
            AssessmentQuestion.id == question_id,
            AssessmentQuestion.training_id == training_id,
            AssessmentQuestion.deleted_at.is_(None)
        ).first()
        if not question:
            raise HTTPException(status_code=404, detail="Assessment question not found")
        
        return AssessmentQuestionResponseSchema(
            id=question.id,
            training_id=question.training_id,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            correct_option=question.correct_option,
            difficulty_level=question.difficulty_level.value if question.difficulty_level else None,
            created_at=question.created_at.isoformat() if question.created_at else None,
            updated_at=question.updated_at.isoformat() if question.updated_at else None
        )
    finally:
        session.close()

@router.put("/{training_id}/assessment/question/{question_id}", summary="Update assessment question", response_model=AssessmentQuestionResponseSchema)
async def update_assessment_question(
    training_id: int,
    question_id: int,
    question: AssessmentQuestionCreateSchema,
    current_user = Depends(admin_auth)
):
    session = SessionLocal()
    try:
        db_question = session.query(AssessmentQuestion).filter(
            AssessmentQuestion.id == question_id,
            AssessmentQuestion.training_id == training_id,
            AssessmentQuestion.deleted_at.is_(None)
        ).first()
        if not db_question:
            raise HTTPException(status_code=404, detail="Assessment question not found")
        db_question.question_text = question.question_text
        db_question.option_a = question.option_a
        db_question.option_b = question.option_b
        db_question.option_c = question.option_c
        db_question.option_d = question.option_d
        db_question.correct_option = question.correct_option
        db_question.difficulty_level = ModelDifficultyLevelEnum(question.difficulty_level)
        session.commit()
        session.refresh(db_question)
        
        return AssessmentQuestionResponseSchema(
            id=db_question.id,
            training_id=db_question.training_id,
            question_text=db_question.question_text,
            option_a=db_question.option_a,
            option_b=db_question.option_b,
            option_c=db_question.option_c,
            option_d=db_question.option_d,
            correct_option=db_question.correct_option,
            difficulty_level=db_question.difficulty_level.value if db_question.difficulty_level else None,
            created_at=db_question.created_at.isoformat() if db_question.created_at else None,
            updated_at=db_question.updated_at.isoformat() if db_question.updated_at else None
        )
    finally:
        session.close()

@router.delete("/{training_id}/assessment/question/{question_id}", summary="Delete assessment question")
async def delete_assessment_question(
    training_id: int,
    question_id: int,
    current_user = Depends(admin_auth)
):
    session = SessionLocal()
    try:
        db_question = session.query(AssessmentQuestion).filter(
            AssessmentQuestion.id == question_id,
            AssessmentQuestion.training_id == training_id,
            AssessmentQuestion.deleted_at.is_(None)
        ).first()
        if not db_question:
            raise HTTPException(status_code=404, detail="Assessment question not found")
        db_question.deleted_at = os.times().elapsed if hasattr(os, 'times') else None
        session.commit()
        return {"message": "Assessment question deleted successfully"}
    finally:
        session.close()

# Training Assignment Modal APIs
@router.get("/{training_id}/assign/users", summary="Get users for assignment", response_model=UserAssignmentListSchema)
async def get_users_for_assignment(
    training_id: int,
    search: Optional[str] = Query(None, description="Search users by name or email"),
    current_user = Depends(admin_auth)
):
    """Get all users available for training assignment with search functionality"""
    try:
        # First verify the training exists
        training = get_training_by_id(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")
        
        # Get users for assignment using existing service
        users_data = get_employees_for_assignment(search=search)
        
        # Convert to response schema
        users = []
        for user_data in users_data:
            user = UserForAssignmentSchema(
                id=user_data["id"],
                full_name=user_data["full_name"],
                email=user_data["email"],
                role=user_data["role"],
                department_name=user_data["department_name"]
            )
            users.append(user)
        
        return UserAssignmentListSchema(
            users=users,
            total_count=len(users)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

@router.post("/{training_id}/assign", summary="Assign training to users")
async def assign_training_to_users(
    training_id: int,
    assignment_data: TrainingAssignmentModalSchema,
    current_user = Depends(admin_auth)
):
    """Assign a training to multiple users with assignment details"""
    try:
        # Validate training_id matches
        if assignment_data.training_id != training_id:
            raise HTTPException(status_code=400, detail="training_id mismatch")
        
        # Verify the training exists
        training = get_training_by_id(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")
        
        # Create assignment data for the existing service
        assignment_request = TrainingAssignmentCreateSchema(
            training_ids=[training_id],
            employee_ids=assignment_data.employee_ids,
            due_date=assignment_data.assignment_date,
            notes=assignment_data.notes
        )
        
        # Use existing service to assign trainings
        assigned_count = assign_trainings_to_employees(assignment_request, assigned_by=current_user.id)
        
        return {
            "message": f"Training assigned successfully to {assigned_count} users",
            "training_id": training_id,
            "assigned_users_count": assigned_count,
            "assignment_date": assignment_data.assignment_date,
            "difficulty_level": assignment_data.difficulty_level,
            "initial_status": assignment_data.initial_status
        }
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to assign training: {str(e)}")

@router.get("/{training_id}/assignments", summary="Get assignments for a specific training")
async def get_training_assignments_api(
    training_id: int,
    current_user = Depends(admin_auth)
):
    """Get all assignments for a specific training"""
    try:
        # Verify the training exists
        training = get_training_by_id(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")
        
        # Get assignments using existing service
        assignments = get_training_assignments_service(training_id=training_id)
        
        return {
            "training_id": training_id,
            "training_title": training.title,
            "assignments": assignments,
            "total_assignments": len(assignments)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch assignments: {str(e)}")

@router.get("/assignment/options", summary="Get assignment options")
async def get_assignment_options(
    current_user = Depends(admin_auth)
):
    """Get available options for training assignment (difficulty levels, statuses)"""
    try:
        return {
            "difficulty_levels": ["Easy", "Medium", "Hard"],
            "initial_statuses": ["Assigned", "In Progress", "Completed", "Cancelled"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch options: {str(e)}")

@router.get("/approved-documents", summary="Get approved documents for training")
async def get_approved_documents(
    current_user = Depends(admin_auth)
):
    """Get all approved documents that can be used for training courses"""
    try:
        from services.documentservice import get_documents_from_db
        
        # Get approved documents
        documents = get_documents_from_db(status="approved")
        
        # Convert to simple format for dropdown
        approved_docs = []
        for doc in documents:
            approved_docs.append({
                "id": doc.id,
                "title": doc.title,
                "document_type": doc.document_type,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "version": doc.version
            })
        
        return {
            "approved_documents": approved_docs,
            "total_count": len(approved_docs)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch approved documents: {str(e)}")

@router.get("/trainers", summary="Get trainers for training")
async def get_trainers(
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    current_user = Depends(admin_auth)
):
    """Get all trainers available for training courses"""
    try:
        trainers = get_trainers_by_department(department_id=department_id)
        
        # Convert to simple format for dropdown
        trainer_list = []
        for trainer in trainers:
            trainer_list.append({
                "id": trainer.id,
                "full_name": trainer.full_name,
                "email": trainer.email,
                "department_name": trainer.department_name
            })
        
        return {
            "trainers": trainer_list,
            "total_count": len(trainer_list)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trainers: {str(e)}")

@router.get("/active-instances", summary="Get active employees for training assignment")
async def get_active_employees(
    search: Optional[str] = Query(None, description="Search employees by name or email"),
    department_id: Optional[int] = Query(None, description="Filter by department ID"),
    current_user = Depends(admin_auth)
):
    """Get all active employees that can be assigned to training courses"""
    try:
        from services.trainingassignmentservice import get_employees_for_assignment
        
        # Get active employees with optional filters
        employees = get_employees_for_assignment(
            search=search,
            department_id=department_id
        )
        
        # Convert to response format
        employee_list = []
        for employee in employees:
            employee_list.append({
                "id": employee["id"],
                "full_name": employee["full_name"],
                "email": employee["email"],
                "emp_id": employee["emp_id"],
                "department_name": employee["department_name"],
                "role": employee["role"],
                "status": "Active",
                "assigned_trainings_count": 0,  # Will be populated if needed
                "completed_trainings_count": 0,  # Will be populated if needed
                "actions": {
                    "can_assign_training": True,
                    "can_view_profile": True,
                    "can_edit": True
                }
            })
        
        return {
            "total_employees": len(employee_list),
            "employees": employee_list,
            "filters": {
                "search": search,
                "department_id": department_id
            }
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch active employees: {str(e)}")

@router.get("/{training_id}/base64", summary="Get training file base64 content")
async def get_training_base64(
    training_id: int,
    current_user = Depends(admin_auth)
):
    """Get the base64 encoded content of a training file"""
    try:
        training = get_training_by_id(training_id)
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")
        
        if not training.file_path or not os.path.exists(training.file_path):
            raise HTTPException(status_code=404, detail="Training file not found")
        
        # Check if base64 already exists in database
        if training.file_base64:
            return {
                "training_id": training_id,
                "file_name": training.file_name,
                "file_size": training.file_size,
                "content_type": training.content_type,
                "base64_data": training.file_base64
            }
        
        # Generate base64 if not exists
        try:
            file_size_bytes = os.path.getsize(training.file_path)
            if file_size_bytes <= 10 * 1024 * 1024:  # 10MB limit
                with open(training.file_path, 'rb') as f:
                    content = f.read()
                    import base64
                    base64_data = base64.b64encode(content).decode('utf-8')
                
                # Update database with base64
                session = SessionLocal()
                try:
                    training.file_base64 = base64_data
                    session.commit()
                finally:
                    session.close()
                
                return {
                    "training_id": training_id,
                    "file_name": training.file_name,
                    "file_size": training.file_size,
                    "content_type": training.content_type,
                    "base64_data": base64_data
                }
            else:
                raise HTTPException(status_code=400, detail=f"File too large for base64 encoding ({file_size_bytes} bytes)")
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate base64: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get training base64: {str(e)}")

