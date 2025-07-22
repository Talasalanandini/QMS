from fastapi import APIRouter, HTTPException, Depends, Header, Request, Query, Path, Body
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from schemas import EmployeeCreate, EmployeeResponse, LoginRequest, LoginResponse, PasswordChangeSchema
from services.employeeserice import create_employee
import secrets
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models import Employee, Role, Token, Department, LoginLog
import datetime
from schemas import EmployeeListItem
from typing import Optional, List

router = APIRouter(tags=["Employee Management"])
security = HTTPBasic()

# Token-based admin authentication

def admin_auth(request: Request):
    session: Session = SessionLocal()
    try:
        authorization = request.headers.get("authorization")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
        access_token = authorization.split(" ", 1)[1]
        token_obj = session.query(Token).filter(Token.token == access_token, Token.revoked == 0).first()
        if not token_obj:
            raise HTTPException(status_code=401, detail="Invalid or revoked token")
        # Check expiry
        expires_at_str = token_obj.expires_at if isinstance(token_obj.expires_at, str) else str(token_obj.expires_at)
        if datetime.datetime.fromisoformat(expires_at_str) < datetime.datetime.utcnow():
            raise HTTPException(status_code=401, detail="Token expired")
        # Check user is admin
        employee = session.query(Employee).filter(Employee.id == token_obj.user_id).first()
        if employee is None:
            raise HTTPException(status_code=401, detail="User not found")
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        if admin_role is None:
            raise HTTPException(status_code=403, detail="Admin role not found")
        if getattr(employee, 'role_id', None) != getattr(admin_role, 'id', None):
            raise HTTPException(status_code=403, detail="Not an admin user")
        return employee.email
    finally:
        session.close()

@router.post('/login', response_model=LoginResponse, summary="Login")
def admin_login(login: LoginRequest):
    session: Session = SessionLocal()
    try:
        employee = session.query(Employee).filter(Employee.email == login.email).first()
        if employee is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Remove admin-only check to allow all employees to log in
        if not bcrypt.verify(login.password, getattr(employee, 'password')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Store login log for all employees
        log = LoginLog(
            user_id=employee.id,
            login_time=datetime.datetime.utcnow()
        )
        session.add(log)
        # Generate access token, etc.
        access_token = secrets.token_urlsafe(64)
        now = datetime.datetime.utcnow()
        expires_at = now + datetime.timedelta(hours=1)
        token_obj = Token(
            user_id=employee.id,
            token=access_token,
            expires_at=expires_at.isoformat(),
            created_at=now.isoformat(),
            revoked=0
        )
        session.add(token_obj)
        session.commit()
        return {"message": "Login successful", "access_token": access_token, "expires_at": expires_at.isoformat()}
    finally:
        session.close()

@router.post('/employees')
def create_employee_api(employee: EmployeeCreate, username: str = Depends(admin_auth)):
    try:
        response, _ = create_employee(employee.dict())
        return response
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get('/employees', response_model=List[EmployeeListItem])
def get_all_employees(
    username: str = Depends(admin_auth),
    role: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    session: Session = SessionLocal()
    try:
        query = session.query(Employee).join(Role, Employee.role_id == Role.id).join(Department, Employee.department_id == Department.id)
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
def get_employee_count(username: str = Depends(admin_auth)):
    session: Session = SessionLocal()
    try:
        count = session.query(Employee).count()
        return {"count": count}
    finally:
        session.close()

@router.get('/employees/{employee_id}', response_model=EmployeeResponse)
def get_employee(employee_id: int, username: str = Depends(admin_auth)):
    session: Session = SessionLocal()
    try:
        employee = session.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
        return employee
    finally:
        session.close()

@router.put('/employees/{employee_id}', response_model=EmployeeResponse)
def update_employee(employee_id: int, employee_update: EmployeeCreate, username: str = Depends(admin_auth)):
    session: Session = SessionLocal()
    try:
        employee = session.query(Employee).filter(Employee.id == employee_id).first()
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

@router.post('/logout', summary="Logout")
def logout(username: str = Depends(admin_auth)):
    session: Session = SessionLocal()
    try:
        employee = session.query(Employee).filter(Employee.email == username).first()
        if not employee:
            raise HTTPException(status_code=404, detail="User not found")
        login_log = session.query(LoginLog).filter(
            LoginLog.user_id == employee.id,
            LoginLog.logout_time == None
        ).order_by(LoginLog.login_time.desc()).first()
        if login_log:
            setattr(login_log, 'logout_time', datetime.datetime.utcnow())
            session.commit()
            return {"message": "Logout successful"}
        else:
            raise HTTPException(status_code=400, detail="No active login session found")
    finally:
        session.close()

@router.post('/employees/{employee_id}/change-password', summary="Admin change user password")
def admin_change_user_password(employee_id: int, new_password: str = Body(...), username: str = Depends(admin_auth)):
    session = SessionLocal()
    try:
        user = session.query(Employee).filter(Employee.id == employee_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        setattr(user, 'password', bcrypt.hash(new_password))
        session.commit()
        return {"message": "Password changed by admin successfully"}
    finally:
        session.close()


