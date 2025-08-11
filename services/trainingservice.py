import datetime
import os
import uuid
from typing import List, Optional
from fastapi import UploadFile
from db.database import SessionLocal
from models import Training, Employee, Department, TrainingTypeEnum, TrainingStatusEnum
from schemas import TrainingCreateSchema, TrainingCreateWithFileSchema, TrainerResponseSchema
from sqlalchemy.orm import joinedload

# Training file upload directory
TRAINING_UPLOAD_DIR = "uploads/trainings"

# Ensure upload directory exists
os.makedirs(TRAINING_UPLOAD_DIR, exist_ok=True)

def save_training_file(file: UploadFile) -> tuple[str, str, int, str, str]:
    """Save uploaded training file and return (file_path, file_name, file_size, file_type, file_base64)"""
    # Generate unique filename
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(TRAINING_UPLOAD_DIR, unique_filename)
    
    # Read file content
    content = file.file.read()
    file_size = len(content)
    
    # Save file
    with open(file_path, "wb") as buffer:
        buffer.write(content)
    
    # Encode as base64 only for smaller files to avoid timeout
    file_base64 = None
    if content and file_size <= 10 * 1024 * 1024:  # 10MB limit
        import base64
        file_base64 = base64.b64encode(content).decode('utf-8')
    elif file_size > 10 * 1024 * 1024:
        print(f"Warning: File too large for base64 encoding ({file_size} bytes). Skipping base64 generation.")
    
    return file_path, file.filename, file_size, file_extension.lower(), file_base64

def add_training_with_file_to_db(training_data: TrainingCreateWithFileSchema, created_by: int):
    """Add a new training with file upload to the database"""
    session = SessionLocal()
    try:
        # Validate that trainer exists
        if training_data.trainer_id:
            trainer = session.query(Employee).filter(Employee.id == training_data.trainer_id, Employee.deleted_at.is_(None)).first()
            if not trainer:
                raise ValueError(f"Trainer with ID {training_data.trainer_id} does not exist")
        
        # Validate content_type
        if training_data.content_type not in ["document", "video"]:
            raise ValueError("Content type must be 'document' or 'video'")
        
        # Validate approved_document_id if content_type is document
        if training_data.content_type == "document" and training_data.approved_document_id:
            from models import Document
            document = session.query(Document).filter(Document.id == training_data.approved_document_id, Document.deleted_at.is_(None)).first()
            if not document:
                raise ValueError(f"Approved document with ID {training_data.approved_document_id} does not exist")
            if document.status != "approved":
                raise ValueError("Document must be approved")
        
        # Parse date strings to datetime
        start_date = datetime.datetime.fromisoformat(training_data.start_date.replace('Z', '+00:00'))
        end_date = datetime.datetime.fromisoformat(training_data.end_date.replace('Z', '+00:00'))
        
        # Get trainer's department for department_id (required by database)
        trainer = session.query(Employee).filter(Employee.id == training_data.trainer_id).first()
        department_id = trainer.department_id if trainer else 1  # Default to department 1 if trainer not found
        
        training = Training(
            title=training_data.title,
            course_code=training_data.course_code,
            description=training_data.description,
            department_id=department_id,  # Use trainer's department
            training_type=TrainingTypeEnum.compliance,  # Default training type
            trainer_id=training_data.trainer_id,
            duration_hours=training_data.duration_hours,
            assigned_date=start_date,  # Map start_date to assigned_date for old schema
            passing_score=training_data.passing_score,
            start_date=start_date,
            end_date=end_date,
            content_type=training_data.content_type,
            mandatory=training_data.mandatory,
            file_path=training_data.file_path,
            file_name=training_data.file_name,
            file_size=training_data.file_size,
            file_type=training_data.file_type,
            file_base64=training_data.file_base64,
            created_by=created_by
        )
        
        session.add(training)
        session.commit()
        session.refresh(training)
        return training
    finally:
        session.close()

def add_training_to_db(training_data: TrainingCreateSchema, created_by: int):
    """Add a new training to the database"""
    session = SessionLocal()
    try:
        # Validate that trainer exists
        if training_data.trainer_id:
            trainer = session.query(Employee).filter(Employee.id == training_data.trainer_id, Employee.deleted_at.is_(None)).first()
            if not trainer:
                raise ValueError(f"Trainer with ID {training_data.trainer_id} does not exist")
        
        # Validate content_type
        if training_data.content_type not in ["document", "video"]:
            raise ValueError("Content type must be 'document' or 'video'")
        
        # Parse date strings to datetime
        start_date = datetime.datetime.fromisoformat(training_data.start_date.replace('Z', '+00:00'))
        end_date = datetime.datetime.fromisoformat(training_data.end_date.replace('Z', '+00:00'))
        
        training = Training(
            title=training_data.title,
            course_code=training_data.course_code,
            description=training_data.description,
            trainer_id=training_data.trainer_id,
            duration_hours=training_data.duration_hours,
            passing_score=training_data.passing_score,
            start_date=start_date,
            end_date=end_date,
            content_type=training_data.content_type,
            mandatory=training_data.mandatory,
            created_by=created_by
        )
        
        session.add(training)
        session.commit()
        session.refresh(training)
        return training
    finally:
        session.close()

def get_trainings_from_db(
    search: Optional[str] = None
):
    """Get trainings with search capability"""
    session = SessionLocal()
    try:
        query = session.query(Training).filter(Training.deleted_at.is_(None))
        
        if search:
            # Search in title, course_code, and description
            search_filter = Training.title.ilike(f"%{search}%") | \
                          Training.course_code.ilike(f"%{search}%") | \
                          Training.description.ilike(f"%{search}%")
            query = query.filter(search_filter)
        
        # Use eager loading to load relationships
        query = query.options(
            joinedload(Training.department),
            joinedload(Training.trainer),
            joinedload(Training.creator)
        )
        
        return query.order_by(Training.created_at.desc()).all()
    finally:
        session.close()

def get_training_by_id(training_id: int):
    """Get a single training by ID"""
    session = SessionLocal()
    try:
        query = session.query(Training).filter(Training.id == training_id, Training.deleted_at.is_(None))
        # Use eager loading to load relationships
        query = query.options(
            joinedload(Training.department),
            joinedload(Training.trainer),
            joinedload(Training.creator)
        )
        return query.first()
    finally:
        session.close()

def delete_training_from_db(training_id: int):
    """Soft delete a training"""
    session = SessionLocal()
    try:
        training = session.query(Training).filter(Training.id == training_id).first()
        if not training:
            return False
        
        # Soft delete
        training.deleted_at = datetime.datetime.utcnow()
        session.commit()
        return True
    finally:
        session.close()

def get_training_statistics():
    """Get training statistics"""
    session = SessionLocal()
    try:
        total_trainings = session.query(Training).filter(Training.deleted_at.is_(None)).count()
        scheduled_trainings = session.query(Training).filter(Training.status == TrainingStatusEnum.scheduled, Training.deleted_at.is_(None)).count()
        in_progress_trainings = session.query(Training).filter(Training.status == TrainingStatusEnum.in_progress, Training.deleted_at.is_(None)).count()
        completed_trainings = session.query(Training).filter(Training.status == TrainingStatusEnum.completed, Training.deleted_at.is_(None)).count()
        cancelled_trainings = session.query(Training).filter(Training.status == TrainingStatusEnum.cancelled, Training.deleted_at.is_(None)).count()
        
        return {
            "total_trainings": total_trainings,
            "scheduled_trainings": scheduled_trainings,
            "in_progress_trainings": in_progress_trainings,
            "completed_trainings": completed_trainings,
            "cancelled_trainings": cancelled_trainings
        }
    finally:
        session.close()

def get_trainers_by_department(department_id: Optional[int] = None):
    """Get all employees who can be trainers, optionally filtered by department"""
    session = SessionLocal()
    try:
        query = session.query(Employee).filter(Employee.deleted_at.is_(None))
        
        if department_id:
            query = query.filter(Employee.department_id == department_id)
        
        employees = query.all()
        result = []
        
        for employee in employees:
            department = session.query(Department).filter(Department.id == employee.department_id).first()
            result.append({
                "id": employee.id,
                "full_name": employee.full_name,
                "email": employee.email,
                "department_name": department.name if department else None
            })
        
        return result
    finally:
        session.close()

def get_training_types():
    """Get all available training types"""
    return [{"value": e.value, "label": e.value} for e in TrainingTypeEnum]

def get_departments():
    """Get all departments"""
    session = SessionLocal()
    try:
        departments = session.query(Department).filter(Department.deleted_at.is_(None)).all()
        return [{"id": dept.id, "name": dept.name} for dept in departments]
    finally:
        session.close()
