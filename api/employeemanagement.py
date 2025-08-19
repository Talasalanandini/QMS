from fastapi import APIRouter, HTTPException, Depends, Request, Query, Path, Body
from schemas import EmployeeCreate, EmployeeResponse, PasswordChangeSchema, CertificateResponseSchema, EmployeeTrainingStatisticsSchema
from services.employeeserice import create_employee
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models import Employee, Role, Department
import datetime
from schemas import EmployeeListItem
from typing import Optional, List
from services.trainingassignmentservice import get_training_assignments as get_training_assignments_service, update_assignment_status
from services.trainingservice import get_training_by_id
from services.certificateservice import generate_training_certificate, save_certificate_to_file
from db.database import SessionLocal
from models import AssessmentSubmission

router = APIRouter(tags=["Employee Management"])

# Import authentication functions from user management
from api.usermanagement import get_current_user

def admin_auth(request: Request):
    employee = get_current_user(request)
    session: Session = SessionLocal()
    try:
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        if admin_role is None:
            raise HTTPException(status_code=403, detail="Admin role not found")
        if getattr(employee, 'role_id', None) != getattr(admin_role, 'id', None):
            raise HTTPException(status_code=403, detail="Not an admin user")
        return employee
    finally:
        session.close()

def reviewer_auth(request: Request):
    employee = get_current_user(request)
    session: Session = SessionLocal()
    try:
        reviewer_role = session.query(Role).filter(Role.name == "Reviewer").first()
        if reviewer_role is None:
            raise HTTPException(status_code=403, detail="Reviewer role not found")
        if getattr(employee, 'role_id', None) != getattr(reviewer_role, 'id', None):
            raise HTTPException(status_code=403, detail="Not a reviewer user")
        return employee
    finally:
        session.close()

def approver_auth(request: Request):
    employee = get_current_user(request)
    session: Session = SessionLocal()
    try:
        approver_role = session.query(Role).filter(Role.name == "Approver").first()
        if approver_role is None:
            raise HTTPException(status_code=403, detail="Approver role not found")
        if getattr(employee, 'role_id', None) != getattr(approver_role, 'id', None):
            raise HTTPException(status_code=403, detail="Not an approver user")
        return employee
    finally:
        session.close()

def employee_auth(request: Request):
    """Authentication for regular employees - allows access to their own data only"""
    employee = get_current_user(request)
    session: Session = SessionLocal()
    try:
        # Check if user is not an admin (employees should not have admin access)
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        if admin_role and getattr(employee, 'role_id', None) == getattr(admin_role, 'id', None):
            raise HTTPException(status_code=403, detail="Admins cannot access employee-specific APIs")
        
        # Allow access for all other roles (Employee, Reviewer, Approver, etc.)
        return employee
    finally:
        session.close()

def admin_or_employee_auth(request: Request):
    """Authentication that allows both admins and employees"""
    employee = get_current_user(request)
    session: Session = SessionLocal()
    try:
        # Allow access for all roles including Admin
        return employee
    finally:
        session.close()

@router.post('/employees')
def create_employee_api(employee: EmployeeCreate, current_user: Employee = Depends(admin_auth)):
    try:
        response, _ = create_employee(employee.dict())
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/employees', response_model=List[EmployeeListItem])
def get_all_employees(
    current_user: Employee = Depends(admin_auth),
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    session: Session = SessionLocal()
    try:
        query = session.query(Employee).join(Role, Employee.role_id == Role.id).join(Department, Employee.department_id == Department.id).filter(Employee.deleted_at.is_(None))
        if role:
            query = query.filter(Role.name == role)
        if department:
            query = query.filter(Department.name == department)
        # If you have a status field, uncomment the next lines:
        # if status:
        #     query = query.filter(Employee.status == status)
        employees = query.all()
        result = []
        for emp in employees:
            result.append({
                "id": emp.id,
                "full_name": emp.full_name,
                "email": emp.email,
                "role": emp.role_obj.name,
                "department": emp.department_obj.name,
            })
        return result
    finally:
        session.close()

@router.get('/employees/count')
def get_employee_count(current_user: Employee = Depends(admin_auth)):
    session: Session = SessionLocal()
    try:
        count = session.query(Employee).filter(Employee.deleted_at.is_(None)).count()
        return {"count": count}
    finally:
        session.close()

@router.get('/my-courses', summary="Get employee's assigned courses")
def get_employee_courses(current_user: Employee = Depends(employee_auth)):
    """Get all training courses assigned to the logged-in employee"""
    try:
        # Get all training assignments for the current employee
        assignments = get_training_assignments_service(employee_id=current_user.id)
        
        # Transform the data to match the "My Courses" dashboard format
        courses = []
        for assignment in assignments:
            # Get training details
            training = get_training_by_id(assignment["training_id"])
            if not training:
                continue
                
            # Generate base64 if missing and file is small enough
            file_base64 = training.file_base64
            if not file_base64 and training.file_path and training.file_size:
                try:
                    import os
                    if training.file_size <= 10 * 1024 * 1024:  # 10MB limit
                        if os.path.exists(training.file_path):
                            with open(training.file_path, 'rb') as f:
                                content = f.read()
                                import base64
                                file_base64 = base64.b64encode(content).decode('utf-8')
                                
                                # Update database with base64
                                session = SessionLocal()
                                try:
                                    training.file_base64 = file_base64
                                    session.commit()
                                finally:
                                    session.close()
                except Exception as e:
                    print(f"Warning: Could not generate base64 for training {training.id}: {e}")
                    file_base64 = None
                
            course = {
                "assignment_id": assignment["id"],  # This is the assignment_id you need!
                "training_id": assignment["training_id"],
                "title": assignment["training_title"] or training.title,
                "course_code": training.course_code,
                "description": training.description,
                "duration_hours": training.duration_hours,
                "assigned_date": assignment["assigned_date"],
                "due_date": assignment["due_date"],
                "status": assignment["status"],
                "completion_date": assignment["completion_date"],
                "score": None,  # Will be populated from assessment submissions
                "certificate_available": False,  # Will be set to True if completed
                "content_type": training.content_type,  # "document" or "video"
                "file_name": training.file_name,
                "file_size": training.file_size,
                "file_type": training.file_type,
                "file_base64": file_base64,
                "actions": {
                    "can_start": assignment["status"] == "assigned",
                    "can_review": assignment["status"] == "completed",
                    "can_download_certificate": assignment["status"] == "completed"
                }
            }
            
            # Add score and certificate info if completed
            if assignment["status"] == "Completed":
                # Get score from assessment_submissions table
                session = SessionLocal()
                try:
                    submission = session.query(AssessmentSubmission).filter(
                        AssessmentSubmission.training_id == assignment["training_id"],
                        AssessmentSubmission.employee_id == current_user.id
                    ).first()
                    
                    if submission:
                        course["score"] = f"{submission.score}%" if submission.score else "N/A"
                        course["certificate_available"] = submission.passed
                    else:
                        course["score"] = "N/A"
                        course["certificate_available"] = False
                finally:
                    session.close()
            
            courses.append(course)
        
        return {
            "total_courses": len(courses),
            "courses": courses
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch courses: {str(e)}")

@router.post('/my-courses/{assignment_id}/start', summary="Start a training course")
def start_course(assignment_id: int, current_user: Employee = Depends(employee_auth)):
    """Mark a training assignment as 'In Progress' when employee starts the course"""
    try:
        # Verify the assignment belongs to the current employee
        assignments = get_training_assignments_service(employee_id=current_user.id)
        assignment_exists = any(a["id"] == assignment_id for a in assignments)
        
        if not assignment_exists:
            raise HTTPException(status_code=404, detail="Training assignment not found or access denied")
        
        # Update assignment status to 'In Progress'
        success = update_assignment_status(assignment_id, "In Progress")
        
        if not success:
            raise HTTPException(status_code=404, detail="Training assignment not found")
        
        return {
            "message": "Course started successfully",
            "assignment_id": assignment_id,
            "status": "In Progress"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start course: {str(e)}")

@router.post('/my-courses/{assignment_id}/complete', summary="Complete a training course")
def complete_course(
    assignment_id: int, 
    current_user: Employee = Depends(employee_auth)
):
    """Mark a training assignment as 'Completed' when employee finishes the course"""
    try:
        # Verify the assignment belongs to the current employee
        assignments = get_training_assignments_service(employee_id=current_user.id)
        assignment_exists = any(a["id"] == assignment_id for a in assignments)
        
        if not assignment_exists:
            raise HTTPException(status_code=404, detail="Training assignment not found or access denied")
        
        # Update assignment status to 'Completed' with completion date
        import datetime
        completion_date = datetime.datetime.utcnow().isoformat()
        success = update_assignment_status(assignment_id, "Completed", completion_date)
        
        if not success:
            raise HTTPException(status_code=404, detail="Training assignment not found")
        
        return {
            "message": "Course completed successfully",
            "assignment_id": assignment_id,
            "status": "Completed",
            "completion_date": completion_date
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete course: {str(e)}")

@router.get('/my-courses/{assignment_id}/certificate', summary="Get course certificate as base64", response_model=CertificateResponseSchema)
def download_certificate(assignment_id: int, current_user: Employee = Depends(employee_auth)):
    """Generate and download a certificate for a completed training course"""
    try:
        # Get assignment details
        assignments = get_training_assignments_service(employee_id=current_user.id)
        assignment = None
        
        for a in assignments:
            if a["id"] == assignment_id:
                assignment = a
                break
        
        if not assignment:
            raise HTTPException(status_code=404, detail="Training assignment not found")
        
        if assignment["status"] != "Completed":
            raise HTTPException(status_code=400, detail="Course must be completed to download certificate")
        
        # Get training details
        training = get_training_by_id(assignment["training_id"])
        if not training:
            raise HTTPException(status_code=404, detail="Training not found")
        
        # Get assessment score
        session = SessionLocal()
        try:
            submission = session.query(AssessmentSubmission).filter(
                AssessmentSubmission.training_id == assignment["training_id"],
                AssessmentSubmission.employee_id == current_user.id
            ).first()
            
            score = submission.score if submission else None
            passed = submission.passed if submission else False
            
        finally:
            session.close()
        
        # Generate certificate data
        certificate_id = f"CERT-{assignment_id:06d}"
        completion_date = assignment["completion_date"] or assignment["assigned_date"]
        score_display = f"{score}%" if score else "N/A"
        
        # Generate PDF certificate
        certificate_buffer = generate_training_certificate(
            employee_name=current_user.full_name,
            employee_email=current_user.email,
            course_title=training.title,
            course_code=training.course_code,
            completion_date=completion_date,
            score=score_display,
            passed=passed,
            certificate_id=certificate_id
        )
        
        # Convert PDF buffer to base64
        import base64
        
        # Get the PDF content as bytes
        pdf_content = certificate_buffer.getvalue()
        
        # Encode to base64
        pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
        
        # Create filename for reference
        filename = f"certificate_{certificate_id}_{current_user.full_name.replace(' ', '_')}.pdf"
        
        # Return base64 encoded PDF with metadata
        return {
            "certificate_id": certificate_id,
            "employee_name": current_user.full_name,
            "employee_email": current_user.email,
            "course_title": training.title,
            "course_code": training.course_code,
            "completion_date": completion_date,
            "score": score_display,
            "passed": passed,
            "filename": filename,
            "pdf_base64": pdf_base64,
            "message": "Certificate generated successfully as base64 string"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate certificate: {str(e)}")



@router.get('/my-courses/statistics', summary="Get employee training statistics", response_model=EmployeeTrainingStatisticsSchema)
def get_employee_training_statistics(current_user: Employee = Depends(employee_auth)):
    """Get training statistics for the logged-in employee dashboard"""
    try:
        # Get all training assignments for the current employee
        assignments = get_training_assignments_service(employee_id=current_user.id)
        
        # Initialize counters
        assigned_count = 0
        completed_count = 0
        in_progress_count = 0
        certificates_count = 0
        
        # Count assignments by status
        for assignment in assignments:
            if assignment["status"] == "Assigned":
                assigned_count += 1
            elif assignment["status"] == "In Progress":
                in_progress_count += 1
            elif assignment["status"] == "Completed":
                completed_count += 1
                # For completed courses, certificate is available
                certificates_count += 1
        
        return {
            "assigned_courses": assigned_count,
            "completed_courses": completed_count,
            "in_progress_courses": in_progress_count,
            "certificates": certificates_count,
            "total_courses": len(assignments)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch training statistics: {str(e)}")

@router.get('/my-certificates', summary="Get employee's completed certificates")
def get_employee_certificates(current_user: Employee = Depends(employee_auth)):
    """Get all completed training certificates for the logged-in employee"""
    try:
        # Get all training assignments for the current employee
        assignments = get_training_assignments_service(employee_id=current_user.id)
        
        # Filter only completed assignments
        completed_assignments = [a for a in assignments if a["status"] == "Completed"]
        
        certificates = []
        for assignment in completed_assignments:
            # Get training details
            training = get_training_by_id(assignment["training_id"])
            if not training:
                continue
            
            # Get assessment score
            session = SessionLocal()
            try:
                submission = session.query(AssessmentSubmission).filter(
                    AssessmentSubmission.training_id == assignment["training_id"],
                    AssessmentSubmission.employee_id == current_user.id
                ).first()
                
                score = submission.score if submission else None
                passed = submission.passed if submission else False
                
            finally:
                session.close()
            
            # Generate certificate data
            certificate_id = f"CERT-{assignment['id']:06d}"
            completion_date = assignment["completion_date"] or assignment["assigned_date"]
            score_display = f"{score}%" if score else "N/A"
            
            # Generate PDF certificate
            certificate_buffer = generate_training_certificate(
                employee_name=current_user.full_name,
                employee_email=current_user.email,
                course_title=training.title,
                course_code=training.course_code,
                completion_date=completion_date,
                score=score_display,
                passed=passed,
                certificate_id=certificate_id
            )
            
            # Convert PDF buffer to base64
            import base64
            pdf_content = certificate_buffer.getvalue()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            
            # Create filename for reference
            filename = f"certificate_{certificate_id}_{current_user.full_name.replace(' ', '_')}.pdf"
            
            certificate = {
                "certificate_id": certificate_id,
                "assignment_id": assignment["id"],
                "training_id": assignment["training_id"],
                "course_title": training.title,
                "course_code": training.course_code,
                "employee_name": current_user.full_name,
                "employee_email": current_user.email,
                "completion_date": completion_date,
                "score": score_display,
                "passed": passed,
                "filename": filename,
                "pdf_base64": pdf_base64,
                "certificate_url": f"/my-courses/{assignment['id']}/certificate"
            }
            
            certificates.append(certificate)
        
        return {
            "total_certificates": len(certificates),
            "certificates": certificates
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch certificates: {str(e)}")

@router.get('/employees/{employee_id}', response_model=EmployeeResponse)
def get_employee(employee_id: int, current_user: Employee = Depends(admin_auth)):
    session: Session = SessionLocal()
    try:
        employee = session.query(Employee).filter(Employee.id == employee_id, Employee.deleted_at.is_(None)).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee
    finally:
        session.close()

@router.put('/employees/{employee_id}', response_model=EmployeeResponse)
def update_employee(employee_id: int, employee_update: EmployeeCreate, current_user: Employee = Depends(admin_auth)):
    session: Session = SessionLocal()
    try:
        employee = session.query(Employee).filter(Employee.id == employee_id, Employee.deleted_at.is_(None)).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        # Update fields
        setattr(employee, "full_name", employee_update.full_name)
        setattr(employee, "email", str(employee_update.email))
        setattr(employee, "phone", employee_update.phone)
        setattr(employee, "department_id", employee_update.department_id)
        setattr(employee, "role_id", employee_update.role_id)
        session.commit()
        session.refresh(employee)
        return employee
    finally:
        session.close()

#-----Employeee-----#

@router.delete('/employees/{employee_id}', summary="Delete employee")
def delete_employee(employee_id: int, current_user: Employee = Depends(admin_auth)):
    """Soft delete an employee by setting deleted_at timestamp"""
    session: Session = SessionLocal()
    try:
        # Check if employee exists
        employee = session.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        
        # Check if trying to delete self
        if employee.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")
        
        # Check if employee is the last admin
        if employee.role_obj.name == "Admin":
            admin_count = session.query(Employee).join(Role, Employee.role_id == Role.id).filter(
                Role.name == "Admin",
                Employee.deleted_at.is_(None)
            ).count()
            if admin_count <= 1:
                raise HTTPException(status_code=400, detail="Cannot delete the last admin user")
        
        # Soft delete by setting deleted_at timestamp
        employee.deleted_at = datetime.datetime.utcnow()
        session.commit()
        
        return {
            "message": f"Employee '{employee.full_name}' has been deleted successfully",
            "employee_id": employee.id,
            "deleted_at": employee.deleted_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete employee: {str(e)}")
    finally:
        session.close()

