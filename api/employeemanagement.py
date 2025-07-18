from fastapi import APIRouter, HTTPException, Depends, Header, Request, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from schemas import EmployeeCreate, EmployeeResponse, LoginRequest, LoginResponse
from services.employeeserice import create_employee
import secrets
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models import Employee, Role, Token, Department
import datetime
from schemas import EmployeeListItem
from typing import Optional, List

router = APIRouter()
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
        if employee.role_id != admin_role.id:
            raise HTTPException(status_code=403, detail="Not an admin user")
        return employee.email
    finally:
        session.close()

@router.post('/login', response_model=LoginResponse)
def admin_login(login: LoginRequest):
    session: Session = SessionLocal()
    try:
        # Find employee by email
        employee = session.query(Employee).filter(Employee.email == login.email).first()
        if employee is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Check if employee is admin
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        if admin_role is None or employee.role_id != admin_role.id:
            raise HTTPException(status_code=403, detail="Not an admin user")
        # Verify password
        if not bcrypt.verify(login.password, getattr(employee, 'password')):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        # Generate access token
        access_token = secrets.token_urlsafe(32)
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

@router.post('/employees', response_model=EmployeeResponse)
def create_employee_api(employee: EmployeeCreate, username: str = Depends(admin_auth)):
    try:
        employee_obj, password = create_employee(employee.dict())
        # Return password in response for demo/testing
        response = employee_obj.__dict__.copy()
        response['password'] = password
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


