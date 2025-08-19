import datetime
from db.database import SessionLocal
from models import (
    CompanyTrainingAssignment, Training, Client, Employee
)

# --- Company CRUD Services ---

def add_company_to_db(company_data):
    session = SessionLocal()
    try:
        company = Client(
            company_name=company_data.company_name,
            timezone=company_data.timezone,
            logo_url=company_data.logo_url
        )
        session.add(company)
        session.commit()
        session.refresh(company)
        return company
    finally:
        session.close()

def get_companies_from_db():
    session = SessionLocal()
    try:
        return session.query(Client).all()
    finally:
        session.close()

def get_company_by_id(company_id: int):
    session = SessionLocal()
    try:
        return session.query(Client).filter(Client.id == company_id).first()
    finally:
        session.close()

def update_company_in_db(company_id: int, company_data):
    session = SessionLocal()
    try:
        company = session.query(Client).filter(Client.id == company_id).first()
        if not company:
            return None
        
        if company_data.company_name is not None:
            company.company_name = company_data.company_name
        if company_data.timezone is not None:
            company.timezone = company_data.timezone
        if company_data.logo_url is not None:
            company.logo_url = company_data.logo_url
        
        session.commit()
        session.refresh(company)
        return company
    finally:
        session.close()

# --- Company Training Assignment Services ---

def get_available_trainings_for_company():
    """Get all available trainings that can be assigned to companies"""
    session = SessionLocal()
    try:
        trainings = session.query(Training).filter(Training.deleted_at == None).all()
        result = []
        for training in trainings:
            result.append({
                "id": training.id,
                "title": training.title,
                "course_code": training.course_code,
                "description": training.description,
                "training_type": training.training_type.value if training.training_type else None,
                "duration_hours": training.duration_hours,
                "passing_score": training.passing_score,
                "mandatory": training.mandatory,
                "status": training.status.value if training.status else None
            })
        return result
    finally:
        session.close()

def assign_trainings_to_company(company_id: int, training_ids: list[int], assigned_by: int, due_date: str = None, notes: str = None):
    """Assign multiple trainings to a company"""
    session = SessionLocal()
    try:
        # Verify company exists
        company = session.query(Client).filter(Client.id == company_id).first()
        if not company:
            return None, "Company not found"
        
        # Verify trainings exist
        trainings = session.query(Training).filter(Training.id.in_(training_ids)).all()
        if len(trainings) != len(training_ids):
            return None, "Some trainings not found"
        
        # Create assignments
        assignments = []
        for training_id in training_ids:
            # Check if assignment already exists
            existing = session.query(CompanyTrainingAssignment).filter(
                CompanyTrainingAssignment.company_id == company_id,
                CompanyTrainingAssignment.training_id == training_id,
                CompanyTrainingAssignment.is_active == True
            ).first()
            
            if existing:
                continue  # Skip if already assigned
            
            # Parse due_date if provided and valid
            parsed_due_date = None
            if due_date and due_date.strip() and due_date.lower() not in ["string", ""]:
                try:
                    parsed_due_date = datetime.datetime.fromisoformat(due_date)
                except ValueError:
                    return None, f"Invalid date format for due_date: {due_date}. Please use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
            
            assignment = CompanyTrainingAssignment(
                company_id=company_id,
                training_id=training_id,
                assigned_by=assigned_by,
                due_date=parsed_due_date,
                notes=notes
            )
            session.add(assignment)
            assignments.append(assignment)
        
        session.commit()
        return assignments, f"Successfully assigned {len(assignments)} trainings to company"
    except Exception as e:
        session.rollback()
        return None, f"Error assigning trainings: {str(e)}"
    finally:
        session.close()

def get_company_training_assignments(company_id: int):
    """Get all training assignments for a specific company"""
    session = SessionLocal()
    try:
        assignments = session.query(CompanyTrainingAssignment).filter(
            CompanyTrainingAssignment.company_id == company_id,
            CompanyTrainingAssignment.is_active == True
        ).all()
        
        result = []
        for assignment in assignments:
            result.append({
                "id": assignment.id,
                "company_id": assignment.company_id,
                "company_name": assignment.company.company_name if assignment.company else None,
                "training_id": assignment.training_id,
                "training_title": assignment.training.title if assignment.training else None,
                "training_code": assignment.training.course_code if assignment.training else None,
                "training_type": assignment.training.training_type.value if assignment.training and assignment.training.training_type else None,
                "duration_hours": assignment.training.duration_hours if assignment.training else None,
                "passing_score": assignment.training.passing_score if assignment.training else None,
                "assigned_by": assignment.assigned_by,
                "assigned_by_name": assignment.assigned_by_user.full_name if assignment.assigned_by_user else None,
                "assigned_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "notes": assignment.notes,
                "is_active": assignment.is_active
            })
        return result
    finally:
        session.close()

def get_all_company_training_assignments():
    """Get all company training assignments"""
    session = SessionLocal()
    try:
        assignments = session.query(CompanyTrainingAssignment).filter(
            CompanyTrainingAssignment.is_active == True
        ).all()
        
        result = []
        for assignment in assignments:
            result.append({
                "id": assignment.id,
                "company_id": assignment.company_id,
                "company_name": assignment.company.company_name if assignment.company else None,
                "training_id": assignment.training_id,
                "training_title": assignment.training.title if assignment.training else None,
                "training_code": assignment.training.course_code if assignment.training else None,
                "training_type": assignment.training.training_type.value if assignment.training and assignment.training.training_type else None,
                "duration_hours": assignment.training.duration_hours if assignment.training else None,
                "passing_score": assignment.training.passing_score if assignment.training else None,
                "assigned_by": assignment.assigned_by,
                "assigned_by_name": assignment.assigned_by_user.full_name if assignment.assigned_by_user else None,
                "assigned_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "notes": assignment.notes,
                "is_active": assignment.is_active
            })
        return result
    finally:
        session.close()

def remove_training_from_company(company_id: int, training_id: int):
    """Remove a training assignment from a company"""
    session = SessionLocal()
    try:
        assignment = session.query(CompanyTrainingAssignment).filter(
            CompanyTrainingAssignment.company_id == company_id,
            CompanyTrainingAssignment.training_id == training_id,
            CompanyTrainingAssignment.is_active == True
        ).first()
        
        if not assignment:
            return False, "Training assignment not found"
        
        assignment.is_active = False
        session.commit()
        return True, "Training removed from company successfully"
    except Exception as e:
        session.rollback()
        return False, f"Error removing training: {str(e)}"
    finally:
        session.close()
