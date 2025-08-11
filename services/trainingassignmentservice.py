import datetime
from typing import List, Optional
from db.database import SessionLocal
from models import TrainingAssignment, Employee, Department, Training, Role, TrainingAssignmentStatusEnum
from schemas import TrainingAssignmentCreateSchema, EmployeeForAssignmentSchema
from sqlalchemy.orm import joinedload

def assign_trainings_to_employees(assignment_data: TrainingAssignmentCreateSchema, assigned_by: int):
    """Assign multiple trainings to multiple employees"""
    session = SessionLocal()
    try:
        assignments = []
        
        # Validate that all trainings exist
        trainings = session.query(Training).filter(
            Training.id.in_(assignment_data.training_ids),
            Training.deleted_at.is_(None)
        ).all()
        if len(trainings) != len(assignment_data.training_ids):
            raise ValueError("One or more training IDs are invalid")
        
        # Validate that all employees exist
        employees = session.query(Employee).filter(
            Employee.id.in_(assignment_data.employee_ids),
            Employee.deleted_at.is_(None)
        ).all()
        if len(employees) != len(assignment_data.employee_ids):
            raise ValueError("One or more employee IDs are invalid")
        
        # Parse due date if provided
        due_date = None
        if assignment_data.due_date:
            due_date = datetime.datetime.fromisoformat(assignment_data.due_date.replace('Z', '+00:00'))
        
        # Create assignments
        for training_id in assignment_data.training_ids:
            for employee_id in assignment_data.employee_ids:
                # Check if assignment already exists
                existing = session.query(TrainingAssignment).filter(
                    TrainingAssignment.training_id == training_id,
                    TrainingAssignment.employee_id == employee_id,
                    TrainingAssignment.deleted_at.is_(None)
                ).first()
                
                if existing:
                    continue  # Skip if already assigned
                
                assignment = TrainingAssignment(
                    training_id=training_id,
                    employee_id=employee_id,
                    assigned_by=assigned_by,
                    due_date=due_date,
                    notes=assignment_data.notes,
                    status=TrainingAssignmentStatusEnum.assigned
                )
                session.add(assignment)
                assignments.append(assignment)
        
        session.commit()
        return len(assignments)
    finally:
        session.close()

def get_employees_for_assignment(
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    role: Optional[str] = None
):
    """Get all employees for training assignment with optional filtering"""
    session = SessionLocal()
    try:
        query = session.query(Employee).filter(Employee.deleted_at.is_(None))
        
        if search:
            query = query.filter(
                (Employee.full_name.ilike(f"%{search}%")) |
                (Employee.email.ilike(f"%{search}%"))
            )
        
        if department_id:
            query = query.filter(Employee.department_id == department_id)
        
        if role:
            query = query.join(Role, Employee.role_id == Role.id)
            query = query.filter(Role.name == role)
        
        # Use eager loading
        query = query.options(
            joinedload(Employee.department_obj),
            joinedload(Employee.role_obj)
        )
        
        employees = query.all()
        result = []
        
        for employee in employees:
            result.append({
                "id": employee.id,
                "full_name": employee.full_name,
                "email": employee.email,
                "department_name": employee.department_obj.name if employee.department_obj else None,
                "role": employee.role_obj.name if employee.role_obj else None,
                "emp_id": str(employee.id)  # Display ID for UI
            })
        
        return result
    finally:
        session.close()

def get_training_assignments(
    employee_id: Optional[int] = None,
    training_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """Get training assignments with optional filtering"""
    session = SessionLocal()
    try:
        query = session.query(TrainingAssignment).filter(TrainingAssignment.deleted_at.is_(None))
        
        if employee_id:
            query = query.filter(TrainingAssignment.employee_id == employee_id)
        
        if training_id:
            query = query.filter(TrainingAssignment.training_id == training_id)
        
        if status:
            try:
                status_enum = TrainingAssignmentStatusEnum(status)
                query = query.filter(TrainingAssignment.status == status_enum)
            except ValueError:
                return []
        
        if search:
            query = query.join(Training, TrainingAssignment.training_id == Training.id)
            query = query.filter(Training.title.ilike(f"%{search}%"))
        
        # Use eager loading
        query = query.options(
            joinedload(TrainingAssignment.training),
            joinedload(TrainingAssignment.employee),
            joinedload(TrainingAssignment.assigned_by_user)
        )
        
        assignments = query.all()
        result = []
        
        for assignment in assignments:
            result.append({
                "id": assignment.id,
                "training_id": assignment.training_id,
                "training_title": assignment.training.title if assignment.training else None,
                "training_type": assignment.training.training_type.value if assignment.training else None,
                "employee_id": assignment.employee_id,
                "employee_name": assignment.employee.full_name if assignment.employee else None,
                "employee_email": assignment.employee.email if assignment.employee else None,
                "department_name": assignment.employee.department_obj.name if assignment.employee and assignment.employee.department_obj else None,
                "assigned_by": assignment.assigned_by,
                "assigned_by_name": assignment.assigned_by_user.full_name if assignment.assigned_by_user else None,
                "assigned_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "completion_date": assignment.completion_date.isoformat() if assignment.completion_date else None,
                "status": assignment.status.value,
                "notes": assignment.notes,
                "created_at": assignment.created_at.isoformat() if assignment.created_at else None,
                "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else None
            })
        
        return result
    finally:
        session.close()

def update_assignment_status(assignment_id: int, status: str, completion_date: Optional[str] = None):
    """Update the status of a training assignment"""
    session = SessionLocal()
    try:
        assignment = session.query(TrainingAssignment).filter(
            TrainingAssignment.id == assignment_id,
            TrainingAssignment.deleted_at.is_(None)
        ).first()
        
        if not assignment:
            return False
        
        try:
            status_enum = TrainingAssignmentStatusEnum(status)
            assignment.status = status_enum
        except ValueError:
            return False
        
        if completion_date and status == "Completed":
            assignment.completion_date = datetime.datetime.fromisoformat(completion_date.replace('Z', '+00:00'))
        
        session.commit()
        return True
    finally:
        session.close()

def get_assignment_statistics():
    """Get training assignment statistics"""
    session = SessionLocal()
    try:
        total_assignments = session.query(TrainingAssignment).filter(TrainingAssignment.deleted_at.is_(None)).count()
        assigned_count = session.query(TrainingAssignment).filter(
            TrainingAssignment.status == TrainingAssignmentStatusEnum.assigned,
            TrainingAssignment.deleted_at.is_(None)
        ).count()
        in_progress_count = session.query(TrainingAssignment).filter(
            TrainingAssignment.status == TrainingAssignmentStatusEnum.in_progress,
            TrainingAssignment.deleted_at.is_(None)
        ).count()
        completed_count = session.query(TrainingAssignment).filter(
            TrainingAssignment.status == TrainingAssignmentStatusEnum.completed,
            TrainingAssignment.deleted_at.is_(None)
        ).count()
        cancelled_count = session.query(TrainingAssignment).filter(
            TrainingAssignment.status == TrainingAssignmentStatusEnum.cancelled,
            TrainingAssignment.deleted_at.is_(None)
        ).count()
        
        return {
            "total_assignments": total_assignments,
            "assigned": assigned_count,
            "in_progress": in_progress_count,
            "completed": completed_count,
            "cancelled": cancelled_count
        }
    finally:
        session.close() 