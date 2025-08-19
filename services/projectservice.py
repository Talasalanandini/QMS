import datetime
from db.database import SessionLocal
from models import Project, ProjectEmployeeAssignment, Employee, Department, ProjectStatusEnum

def create_project(project_data, created_by: int):
    """Create a new project and assign employees"""
    session = SessionLocal()
    try:
        # Parse dates if provided
        start_date = None
        end_date = None
        
        if project_data.start_date:
            try:
                start_date = datetime.datetime.fromisoformat(project_data.start_date)
            except ValueError:
                return None, f"Invalid start_date format: {project_data.start_date}. Please use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
        
        if project_data.end_date:
            try:
                end_date = datetime.datetime.fromisoformat(project_data.end_date)
            except ValueError:
                return None, f"Invalid end_date format: {project_data.end_date}. Please use ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
        
        # Create project
        project = Project(
            name=project_data.name,
            description=project_data.description,
            status=project_data.status,
            start_date=start_date,
            end_date=end_date,
            project_manager_id=project_data.project_manager_id,
            department_id=project_data.department_id,
            created_by=created_by
        )
        
        session.add(project)
        session.flush()  # Get the project ID
        
        # Assign employees to project
        if project_data.employee_ids:
            for employee_id in project_data.employee_ids:
                # Check if employee exists
                employee = session.query(Employee).filter(Employee.id == employee_id).first()
                if not employee:
                    session.rollback()
                    return None, f"Employee with ID {employee_id} not found"
                
                # Check if assignment already exists
                existing = session.query(ProjectEmployeeAssignment).filter(
                    ProjectEmployeeAssignment.project_id == project.id,
                    ProjectEmployeeAssignment.employee_id == employee_id,
                    ProjectEmployeeAssignment.is_active == True
                ).first()
                
                if existing:
                    continue  # Skip if already assigned
                
                assignment = ProjectEmployeeAssignment(
                    project_id=project.id,
                    employee_id=employee_id,
                    assigned_by=created_by
                )
                session.add(assignment)
        
        session.commit()
        session.refresh(project)
        return project, "Project created successfully"
        
    except Exception as e:
        session.rollback()
        return None, f"Error creating project: {str(e)}"
    finally:
        session.close()

def get_all_projects():
    """Get all active projects"""
    session = SessionLocal()
    try:
        projects = session.query(Project).filter(Project.is_active == True).all()
        result = []
        for project in projects:
            result.append({
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status.value if project.status else None,
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "end_date": project.end_date.isoformat() if project.end_date else None,
                "project_manager_id": project.project_manager_id,
                "project_manager_name": project.project_manager.full_name if project.project_manager else None,
                "department_id": project.department_id,
                "department_name": project.department.name if project.department else None,
                "created_by": project.created_by,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "is_active": project.is_active
            })
        return result
    finally:
        session.close()

def get_project_by_id(project_id: int):
    """Get a specific project by ID"""
    session = SessionLocal()
    try:
        project = session.query(Project).filter(Project.id == project_id, Project.is_active == True).first()
        if not project:
            return None
        
        return {
            "id": project.id,
            "name": project.name,
            "description": project.description,
            "status": project.status.value if project.status else None,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "project_manager_id": project.project_manager_id,
            "project_manager_name": project.project_manager.full_name if project.project_manager else None,
            "department_id": project.department_id,
            "department_name": project.department.name if project.department else None,
            "created_by": project.created_by,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
            "is_active": project.is_active
        }
    finally:
        session.close()

def update_project(project_id: int, project_data):
    """Update an existing project - only specified fields will be changed, others remain unchanged"""
    session = SessionLocal()
    try:
        project = session.query(Project).filter(Project.id == project_id, Project.is_active == True).first()
        if not project:
            return None, "Project not found"
        
        # Only update fields that are explicitly provided (not None)
        # All other fields will remain exactly as they are
        
        if project_data.name is not None:
            project.name = project_data.name
        # If name is None, project.name remains unchanged
        
        if project_data.description is not None:
            project.description = project_data.description
        # If description is None, project.description remains unchanged
        
        if project_data.status is not None:
            project.status = project_data.status
        # If status is None, project.status remains unchanged
        
        if project_data.start_date is not None:
            try:
                project.start_date = datetime.datetime.fromisoformat(project_data.start_date)
            except ValueError:
                return None, f"Invalid start_date format: {project_data.start_date}"
        # If start_date is None, project.start_date remains unchanged
        
        if project_data.end_date is not None:
            try:
                project.end_date = datetime.datetime.fromisoformat(project_data.end_date)
            except ValueError:
                return None, f"Invalid end_date format: {project_data.end_date}"
        # If end_date is None, project.end_date remains unchanged
        
        if project_data.project_manager_id is not None:
            project.project_manager_id = project_data.project_manager_id
        # If project_manager_id is None, project.project_manager_id remains unchanged
        
        if project_data.department_id is not None:
            project.department_id = project_data.department_id
        # If department_id is None, project.department_id remains unchanged
        
        # Note: created_by, created_at, updated_at, and is_active are never changed
        # They remain exactly as they were
        
        session.commit()
        session.refresh(project)
        return project, "Project updated successfully - only specified fields were changed"
        
    except Exception as e:
        session.rollback()
        return None, f"Error updating project: {str(e)}"
    finally:
        session.close()

def delete_project(project_id: int):
    """Soft delete a project"""
    session = SessionLocal()
    try:
        project = session.query(Project).filter(Project.id == project_id, Project.is_active == True).first()
        if not project:
            return False, "Project not found"
        
        project.is_active = False
        session.commit()
        return True, "Project deleted successfully"
        
    except Exception as e:
        session.rollback()
        return False, f"Error deleting project: {str(e)}"
    finally:
        session.close()

def get_project_employees(project_id: int):
    """Get all employees assigned to a specific project"""
    session = SessionLocal()
    try:
        assignments = session.query(ProjectEmployeeAssignment).filter(
            ProjectEmployeeAssignment.project_id == project_id,
            ProjectEmployeeAssignment.is_active == True
        ).all()
        
        result = []
        for assignment in assignments:
            result.append({
                "id": assignment.id,
                "project_id": assignment.project_id,
                "project_name": assignment.project.name if assignment.project else None,
                "employee_id": assignment.employee_id,
                "employee_name": assignment.employee.full_name if assignment.employee else None,
                "employee_email": assignment.employee.email if assignment.employee else None,
                "department_name": assignment.employee.department_obj.name if assignment.employee and assignment.employee.department_obj else None,
                "assigned_by": assignment.assigned_by,
                "assigned_by_name": assignment.assigned_by_user.full_name if assignment.assigned_by_user else None,
                "assigned_date": assignment.assigned_date.isoformat() if assignment.assigned_date else None,
                "is_active": assignment.is_active
            })
        return result
    finally:
        session.close()

def get_employees_for_project_assignment():
    """Get all employees that can be assigned to projects"""
    session = SessionLocal()
    try:
        employees = session.query(Employee).filter(Employee.deleted_at == None).all()
        result = []
        for employee in employees:
            result.append({
                "id": employee.id,
                "full_name": employee.full_name,
                "email": employee.email,
                "department_name": employee.department_obj.name if employee.department_obj else None,
                "role": employee.role_obj.name if employee.role_obj else None
            })
        return result
    finally:
        session.close()

def get_filter_options():
    """Get available options for status, department, and employee filters"""
    session = SessionLocal()
    try:
        # Get all available project statuses
        statuses = [status.value for status in ProjectStatusEnum]
        
        # Get all departments
        departments = session.query(Department).filter(Department.deleted_at == None).all()
        department_options = [
            {"id": dept.id, "name": dept.name} 
            for dept in departments
        ]
        
        # Get all employees (for project manager and assigned employee filters)
        employees = session.query(Employee).filter(Employee.deleted_at == None).all()
        employee_options = [
            {"id": emp.id, "name": emp.full_name, "email": emp.email} 
            for emp in employees
        ]
        
        return {
            "statuses": statuses,
            "departments": department_options,
            "employees": employee_options
        }
    finally:
        session.close()

def search_projects(status: str = None, department_name: str = None, employee_name: str = None):
    """Search and filter projects by status, department name, or employee name"""
    session = SessionLocal()
    try:
        query = session.query(Project).filter(Project.is_active == True)
        
        # Filter by status
        if status:
            query = query.filter(Project.status == status)
        
        # Filter by department name (partial match, case-insensitive)
        if department_name:
            query = query.join(Department).filter(
                Department.name.ilike(f"%{department_name}%")
            )
        
        # Filter by employee name (partial match, case-insensitive)
        # Employee can be project manager OR assigned to the project
        if employee_name:
            # First, find employees matching the name
            matching_employees = session.query(Employee).filter(
                Employee.full_name.ilike(f"%{employee_name}%"),
                Employee.deleted_at == None
            ).all()
            
            if matching_employees:
                employee_ids = [emp.id for emp in matching_employees]
                
                # Filter projects where employee is project manager OR assigned
                query = query.filter(
                    (Project.project_manager_id.in_(employee_ids)) |
                    (Project.id.in_(
                        session.query(ProjectEmployeeAssignment.project_id)
                        .filter(ProjectEmployeeAssignment.employee_id.in_(employee_ids))
                        .filter(ProjectEmployeeAssignment.is_active == True)
                    ))
                )
            else:
                # No matching employees found, return empty result
                return []
        
        projects = query.all()
        result = []
        for project in projects:
            result.append({
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status.value if project.status else None,
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "end_date": project.end_date.isoformat() if project.end_date else None,
                "project_manager_id": project.project_manager_id,
                "project_manager_name": project.project_manager.full_name if project.project_manager else None,
                "department_id": project.department_id,
                "department_name": project.department.name if project.department else None,
                "created_by": project.created_by,
                "created_at": project.created_at.isoformat() if project.created_at else None,
                "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                "is_active": project.is_active
            })
        return result
    finally:
        session.close()

# ===== Gantt / Timeline helpers =====

def get_projects_timeline():
    """Return Gantt-friendly timeline data with today's position and progress for each active project."""
    session = SessionLocal()
    try:
        projects = session.query(Project).filter(Project.is_active == True).all()
        today = datetime.date.today()
        items = []
        for p in projects:
            if not p.start_date or not p.end_date:
                continue
            start = p.start_date.date() if isinstance(p.start_date, datetime.datetime) else p.start_date
            end = p.end_date.date() if isinstance(p.end_date, datetime.datetime) else p.end_date
            if end < start:
                # swap if entered incorrectly
                start, end = end, start
            total_days = max((end - start).days + 1, 1)
            if today < start:
                status = "Not Started"
                elapsed_days = 0
                progress = 0.0
            elif today > end:
                status = "Completed"
                elapsed_days = total_days
                progress = 1.0
            else:
                status = "In Progress"
                elapsed_days = (today - start).days + 1
                progress = elapsed_days / total_days
            remaining_days = max(total_days - elapsed_days, 0)
            today_index = min(max((today - start).days, 0), total_days)
            today_position_percent = round(min(max((today_index / total_days) * 100, 0), 100), 2)
            items.append({
                "id": p.id,
                "name": p.name,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "total_days": total_days,
                "elapsed_days": min(elapsed_days, total_days),
                "remaining_days": remaining_days,
                "progress_percent": round(progress * 100, 2),
                "today_in_range": start <= today <= end,
                "today_index": today_index,
                "today_position_percent": today_position_percent,
                "status": status,
                "project_manager_name": p.project_manager.full_name if p.project_manager else None,
                "department_name": p.department.name if p.department else None,
            })
        return items
    finally:
        session.close()

def get_projects_timeline_by_view(view_type: str = "month"):
    """Return timeline data formatted for specific view types: day, week, or month"""
    print(f"DEBUG: Received view_type: '{view_type}'")  # Debug log
    session = SessionLocal()
    try:
        projects = session.query(Project).filter(Project.is_active == True).all()
        today = datetime.date.today()
        items = []
        
        for p in projects:
            if not p.start_date or not p.end_date:
                continue
                
            start = p.start_date.date() if isinstance(p.start_date, datetime.datetime) else p.start_date
            end = p.end_date.date() if isinstance(p.end_date, datetime.datetime) else p.end_date
            if end < start:
                start, end = end, start
                
            # Calculate timeline data
            total_days = max((end - start).days + 1, 1)
            if today < start:
                status = "Not Started"
                elapsed_days = 0
                progress = 0.0
            elif today > end:
                status = "Completed"
                elapsed_days = total_days
                progress = 1.0
            else:
                status = "In Progress"
                elapsed_days = (today - start).days + 1
                progress = elapsed_days / total_days
                
            remaining_days = max(total_days - elapsed_days, 0)
            today_index = min(max((today - start).days, 0), total_days)
            today_position_percent = round(min(max((today_index / total_days) * 100, 0), 100), 2)
            
            # Calculate timeline view positioning
            timeline_view_info = calculate_timeline_view_position(start, end, today, view_type)
            
            print(f"DEBUG: Processing view_type: '{view_type}' for project {p.name}")  # Debug log
            
            # Format dates based on view type
            if view_type == "day":
                print(f"DEBUG: Using DAY view for {p.name}")  # Debug log
                start_formatted = start.strftime("%a, %d")  # "Wed, 06"
                end_formatted = end.strftime("%a, %d")      # "Thu, 13"
                duration_text = f"{total_days} days"
                timeline_units = generate_day_timeline(start, end)
                
            elif view_type == "week":
                print(f"DEBUG: Using WEEK view for {p.name}")  # Debug log
                start_formatted = start.strftime("%a, %d %b")  # "Wed, 06 Aug"
                end_formatted = end.strftime("%a, %d %b")      # "Thu, 13 Nov"
                duration_text = f"{total_days // 7} weeks, {total_days % 7} days"
                timeline_units = generate_week_timeline(start, end)
                
            elif view_type == "month":
                print(f"DEBUG: Using MONTH view for {p.name}")  # Debug log
                start_formatted = start.strftime("%b %Y")  # "Aug 2025"
                end_formatted = end.strftime("%b %Y")      # "Nov 2025"
                duration_text = f"{((end.year - start.year) * 12 + end.month - start.month)} months"
                timeline_units = generate_month_timeline(start, end)
            else:
                print(f"DEBUG: Unknown view_type '{view_type}', defaulting to month view for {p.name}")  # Debug log
                start_formatted = start.strftime("%b %Y")  # "Aug 2025"
                end_formatted = end.strftime("%b %Y")      # "Nov 2025"
                duration_text = f"{((end.year - start.year) * 12 + end.month - start.month)} months"
                timeline_units = generate_month_timeline(start, end)
            
            items.append({
                "id": p.id,
                "name": p.name,
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "start_date_formatted": start_formatted,
                "end_date_formatted": end_formatted,
                "total_days": total_days,
                "elapsed_days": min(elapsed_days, total_days),
                "remaining_days": remaining_days,
                "progress_percent": round(progress * 100, 2),
                "today_in_range": start <= today <= end,
                "today_index": today_index,
                "today_position_percent": today_position_percent,
                "status": status,
                "duration_text": duration_text,
                "timeline_units": timeline_units,
                "timeline_view_info": timeline_view_info,
                "project_manager_name": p.project_manager.full_name if p.project_manager else None,
                "department_name": p.department.name if p.department else None,
            })
        return items
    finally:
        session.close()

def calculate_timeline_view_position(start_date: datetime.date, end_date: datetime.date, today: datetime.date, view_type: str):
    """Calculate optimal timeline view position to center on today's date when project is active"""
    if not (start_date <= today <= end_date):
        return {
            "should_center": False,
            "center_position": 0,
            "visible_range_start": 0,
            "visible_range_end": 0
        }
    
    if view_type == "day":
        total_days = (end_date - start_date).days + 1
        today_offset = (today - start_date).days
        center_position = today_offset / total_days
        
        # Show 30 days around today
        visible_days = 30
        start_offset = max(0, today_offset - visible_days // 2)
        end_offset = min(total_days - 1, today_offset + visible_days // 2)
        
        return {
            "should_center": True,
            "center_position": round(center_position * 100, 2),
            "visible_range_start": start_offset,
            "visible_range_end": end_offset,
            "visible_days": visible_days
        }
        
    elif view_type == "week":
        total_weeks = ((end_date - start_date).days + 6) // 7
        today_week = (today - start_date).days // 7
        center_position = today_week / total_weeks if total_weeks > 0 else 0
        
        # Show 8 weeks around today
        visible_weeks = 8
        start_week = max(0, today_week - visible_weeks // 2)
        end_week = min(total_weeks - 1, today_week + visible_weeks // 2)
        
        return {
            "should_center": True,
            "center_position": round(center_position * 100, 2),
            "visible_range_start": start_week,
            "visible_range_end": end_week,
            "visible_weeks": visible_weeks
        }
        
    else:  # month view
        total_months = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
        today_month = (today.year - start_date.year) * 12 + today.month - start_date.month
        center_position = today_month / total_months if total_months > 0 else 0
        
        # Show 6 months around today
        visible_months = 6
        start_month = max(0, today_month - visible_months // 2)
        end_month = min(total_months - 1, today_month + visible_months // 2)
        
        return {
            "should_center": True,
            "center_position": round(center_position * 100, 2),
            "visible_range_start": start_month,
            "visible_range_end": end_month,
            "visible_months": visible_months
        }

def generate_day_timeline(start_date: datetime.date, end_date: datetime.date):
    """Generate day-level timeline units for Gantt chart"""
    timeline = []
    current = start_date
    while current <= end_date:
        timeline.append({
            "date": current.isoformat(),
            "day": current.strftime("%a"),
            "date_num": current.day,
            "formatted": current.strftime("%a, %d")
        })
        current += datetime.timedelta(days=1)
    return timeline

def generate_week_timeline(start_date: datetime.date, end_date: datetime.date):
    """Generate week-level timeline units for Gantt chart"""
    timeline = []
    
    # Start from the beginning of the week containing the start date
    current = start_date - datetime.timedelta(days=start_date.weekday())
    
    # End at the end of the week containing the end date
    end_week = end_date + datetime.timedelta(days=6 - end_date.weekday())
    
    while current <= end_week:
        week_start = current
        week_end = current + datetime.timedelta(days=6)
        
        # Check if this week overlaps with the project
        if week_end >= start_date and week_start <= end_date:
            # Calculate how much of this week the project covers
            week_project_start = max(week_start, start_date)
            week_project_end = min(week_end, end_date)
            
            # Calculate the percentage of the week covered by the project
            week_days = 7
            project_days_in_week = (week_project_end - week_project_start).days + 1
            coverage_percentage = (project_days_in_week / week_days) * 100
            
            timeline.append({
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
                "formatted": f"{week_start.strftime('%d %b')} - {week_end.strftime('%d %b')}",
                "project_start_in_week": week_project_start.isoformat(),
                "project_end_in_week": week_project_end.isoformat(),
                "coverage_percentage": round(coverage_percentage, 2),
                "is_full_week": week_project_start == week_start and week_project_end == week_end,
                "is_partial_start": week_project_start > week_start,
                "is_partial_end": week_project_end < week_end
            })
        
        current += datetime.timedelta(days=7)
    
    return timeline

def generate_month_timeline(start_date: datetime.date, end_date: datetime.date):
    """Generate month-level timeline units for Gantt chart"""
    timeline = []
    
    # Start from the beginning of the month containing the start date
    current = start_date.replace(day=1)
    
    # End at the end of the month containing the end date
    end_month = end_date.replace(day=1)
    if end_date.month == 12:
        end_month = end_month.replace(year=end_month.year + 1, month=1)
    else:
        end_month = end_month.replace(month=end_month.month + 1)
    
    while current < end_month:
        # Calculate the month span
        month_start = current
        if current.month == 12:
            month_end = current.replace(year=current.year + 1, month=1) - datetime.timedelta(days=1)
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            month_end = current.replace(month=current.month + 1) - datetime.timedelta(days=1)
            next_month = current.replace(month=current.month + 1)
        
        # Check if this month overlaps with the project
        if month_end >= start_date and month_start <= end_date:
            # Calculate how much of this month the project covers
            month_project_start = max(month_start, start_date)
            month_project_end = min(month_end, end_date)
            
            # Calculate the percentage of the month covered by the project
            month_days = (month_end - month_start).days + 1
            project_days_in_month = (month_project_end - month_project_start).days + 1
            coverage_percentage = (project_days_in_month / month_days) * 100
            
            timeline.append({
                "month": current.strftime("%B"),
                "year": current.year,
                "formatted": current.strftime("%b %Y"),
                "month_start": month_start.isoformat(),
                "month_end": month_end.isoformat(),
                "project_start_in_month": month_project_start.isoformat(),
                "project_end_in_month": month_project_end.isoformat(),
                "coverage_percentage": round(coverage_percentage, 2),
                "is_full_month": month_project_start == month_start and month_project_end == month_end,
                "is_partial_start": month_project_start > month_start,
                "is_partial_end": month_project_end < month_end
            })
        
        current = next_month
    
    return timeline
