from fastapi import APIRouter, Depends, HTTPException, status
from schemas import (
    ClientCreateSchema, 
    ClientEditSchema, 
    ClientListResponseSchema, 
    ClientResponseSchema,
    CompanyTrainingAssignmentCreateSchema,
    CompanyTrainingAssignmentListResponseSchema,
    AvailableTrainingListForCompanySchema
)
from api.employeemanagement import admin_auth
from models import Employee
from services.companyservices import add_company_to_db, get_companies_from_db, get_company_by_id, update_company_in_db
from services.companyservices import (
    get_available_trainings_for_company, 
    assign_trainings_to_company, 
    get_company_training_assignments,
    get_all_company_training_assignments,
    remove_training_from_company
)
from services.changecontrolservice import create_change_control, get_change_control_details


def get_current_user():
    # Dummy user for testing
    class User:
        id = 1
        is_admin = True
    return User()

def admin_required(current_user=Depends(get_current_user)):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

router = APIRouter(
    prefix="/company",
    tags=["Company Management"],
    dependencies=[Depends(admin_auth)]
)

@router.post("/add", summary="Add new company")
def add_company(company_data: ClientCreateSchema):
    company = add_company_to_db(company_data)
    return {"message": "Company added successfully", "company_id": company.id}



@router.get("/all", summary="View all companies")
def view_all_companies():
    companies = get_companies_from_db()
    result = []
    for company in companies:
        # Format the creation date
        created_date = None
        if hasattr(company, 'created_at') and company.created_at:
            created_date = company.created_at.strftime("%m/%d/%Y")
        else:
            created_date = "8/3/2025"  # Fallback date
        
        result.append({
            "id": company.id,
            "company_name": company.company_name,
            "timezone": getattr(company, 'timezone', 'UTC'),
            "status": "Active",  # Default status for all companies
            "created": created_date,
            "logo_url": getattr(company, 'logo_url', None)
        })
    return result

@router.get("/{company_id}", summary="Get company by ID", response_model=ClientResponseSchema)
def get_company(company_id: int):
    company = get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {
        "id": company.id,
        "company_name": company.company_name,
        "timezone": getattr(company, 'timezone', 'UTC'),
        "logo_url": getattr(company, 'logo_url', None)
    }

@router.put("/{company_id}", summary="Edit company")
def edit_company(company_id: int, company_data: ClientEditSchema):
    updated_company = update_company_in_db(company_id, company_data)
    if not updated_company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    return {"message": "Company updated successfully", "company_id": updated_company.id}

# Company Training Assignment Endpoints
@router.get("/trainings/available", summary="Get all available trainings for companies")
def get_available_trainings():
    """Get all available trainings that can be assigned to companies"""
    trainings = get_available_trainings_for_company()
    return trainings

@router.post("/trainings/assign", summary="Assign trainings to a company")
def assign_trainings_to_company_endpoint(assignment_data: CompanyTrainingAssignmentCreateSchema, current_user: Employee = Depends(admin_auth)):
    """Assign multiple trainings to a company"""
    assignments, message = assign_trainings_to_company(
        company_id=assignment_data.company_id,
        training_ids=assignment_data.training_ids,
        assigned_by=current_user.id,
        due_date=assignment_data.due_date,
        notes=assignment_data.notes
    )
    
    if not assignments:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "assignments_count": len(assignments)}

@router.get("/{company_id}/trainings", summary="Get all training assignments for a company")
def get_company_trainings(company_id: int):
    """Get all training assignments for a specific company"""
    assignments = get_company_training_assignments(company_id)
    return assignments

@router.get("/trainings/assignments", summary="Get all company training assignments")
def get_all_company_trainings():
    """Get all company training assignments across all companies"""
    assignments = get_all_company_training_assignments()
    return assignments

@router.delete("/{company_id}/trainings/{training_id}", summary="Remove a training assignment from a company")
def remove_company_training(company_id: int, training_id: int):
    """Remove a specific training assignment from a company"""
    success, message = remove_training_from_company(company_id, training_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}

@router.get("/dashboard/statistics", summary="Get dashboard statistics")
def get_dashboard_statistics():
    """Get dashboard statistics for companies and training assignments"""
    try:
        # Get total companies
        companies = get_companies_from_db()
        total_companies = len(companies)
        
        # Get total assigned trainings
        all_assignments = get_all_company_training_assignments()
        trainings_assigned = len(all_assignments)
        
        # Get active companies (companies with at least one training assignment)
        active_companies = len(set(assignment["company_id"] for assignment in all_assignments))
        
        # For now, pending approvals is 0 (you can modify this logic based on your requirements)
        pending_approvals = 0
        
        return {
            "total_companies": total_companies,
            "trainings_assigned": trainings_assigned,
            "active_companies": active_companies,
            "pending_approvals": pending_approvals
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard statistics: {str(e)}")


