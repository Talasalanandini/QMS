from fastapi import APIRouter, Depends, HTTPException, Query
from schemas import (
    ProjectCreateSchema, 
    ProjectEditSchema, 
    ProjectResponseSchema,
    ProjectListResponseSchema,
    ProjectEmployeeAssignmentSchema,
    EmployeeListForProjectSchema
)
from api.employeemanagement import admin_auth
from models import Employee
from services.projectservice import (
    create_project,
    get_all_projects,
    get_project_by_id,
    update_project,
    delete_project,
    get_project_employees,
    get_employees_for_project_assignment,
    get_projects_timeline,
    get_projects_timeline_by_view,
    search_projects,
    get_filter_options
)

router = APIRouter(
    prefix="/projects",
    tags=["Project Management"],
    dependencies=[Depends(admin_auth)]
)

@router.post("/create", summary="Create new project")
def create_new_project(project_data: ProjectCreateSchema, current_user: Employee = Depends(admin_auth)):
    """Create a new project and assign employees"""
    project, message = create_project(project_data, current_user.id)
    
    if not project:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "project_id": project.id}

@router.get("/all", summary="Get all projects")
def get_all_projects_endpoint():
    """Get all active projects"""
    projects = get_all_projects()
    return projects

@router.get("/search", summary="Search and filter projects")
def search_projects_endpoint(
    status: str = Query(None, description="Filter by project status"),
    department_name: str = Query(None, description="Filter by department name (partial match)"),
    employee_name: str = Query(None, description="Filter by employee name (partial match)")
):
    """Search and filter projects by status, department name, or employee name"""
    projects = search_projects(status=status, department_name=department_name, employee_name=employee_name)
    return projects

@router.get("/filters/options", summary="Get available filter options")
def get_filter_options_endpoint():
    """Get available options for status, department, and employee filters"""
    options = get_filter_options()
    return options

@router.get("/timeline", summary="Get projects timeline (Gantt data)")
def get_projects_timeline_endpoint(view: str = Query("month", description="Timeline view: day, week, or month")):
    """Return Gantt-friendly timeline data with today's position and progress for each project"""
    if view not in ["day", "week", "month"]:
        raise HTTPException(status_code=400, detail="View must be 'day', 'week', or 'month'")
    
    data = get_projects_timeline_by_view(view)
    return data

@router.get("/employees/available", summary="Get employees for project assignment")
def get_available_employees_endpoint():
    """Get all employees that can be assigned to projects"""
    employees = get_employees_for_project_assignment()
    return employees

@router.get("/{project_id}", summary="Get project by ID")
def get_project_endpoint(project_id: int):
    """Get a specific project by ID"""
    project = get_project_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project

@router.put("/{project_id}", summary="Update project")
def update_project_endpoint(project_id: int, project_data: ProjectEditSchema):
    """Update an existing project"""
    project, message = update_project(project_id, project_data)
    
    if not project:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message, "project_id": project.id}

@router.delete("/{project_id}", summary="Delete project")
def delete_project_endpoint(project_id: int):
    """Soft delete a project"""
    success, message = delete_project(project_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}

@router.get("/{project_id}/employees", summary="Get project employees")
def get_project_employees_endpoint(project_id: int):
    """Get all employees assigned to a specific project"""
    employees = get_project_employees(project_id)
    return employees
