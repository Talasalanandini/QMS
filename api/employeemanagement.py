from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from schemas import EmployeeCreate, EmployeeResponse, LoginRequest, LoginResponse
from services.employeeserice import create_employee
import secrets
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models import Employee, Role

router = APIRouter()
security = HTTPBasic()

# Updated admin_auth to check DB for admin credentials

def admin_auth(credentials: HTTPBasicCredentials = Depends(security)):
    session: Session = SessionLocal()
    try:
        employee = session.query(Employee).filter(Employee.email == credentials.username).first()
        if employee is None:
            raise HTTPException(status_code=401, detail="Invalid admin credentials")
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        if admin_role is None or employee.role_id != admin_role.id:
            raise HTTPException(status_code=403, detail="Not an admin user")
        if not bcrypt.verify(credentials.password, getattr(employee, 'password')):
            raise HTTPException(status_code=401, detail="Invalid admin credentials")
        return credentials.username
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
        return {"message": "Login successful"}
    finally:
        session.close()
