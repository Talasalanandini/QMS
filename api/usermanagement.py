from fastapi import APIRouter, HTTPException, Depends, Request, Body
from schemas import LoginRequest, LoginResponse
import secrets
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models import Employee, Token, LoginLog
import datetime
from datetime import timezone

router = APIRouter(tags=["User Management"])

# Token-based authentication
def get_current_user(request: Request):
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
        if datetime.datetime.fromisoformat(expires_at_str) < datetime.datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="Token expired")
        # Get user
        employee = session.query(Employee).filter(Employee.id == token_obj.user_id).first()
        if employee is None:
            raise HTTPException(status_code=401, detail="User not found")
        return employee
    finally:
        session.close()

def admin_auth(request: Request):
    employee = get_current_user(request)
    session: Session = SessionLocal()
    try:
        from models import Role
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        if admin_role is None:
            raise HTTPException(status_code=403, detail="Admin role not found")
        if getattr(employee, 'role_id', None) != getattr(admin_role, 'id', None):
            raise HTTPException(status_code=403, detail="Not an admin user")
        return employee
    finally:
        session.close()

@router.post('/login', response_model=LoginResponse, summary="Login")
def user_login(login: LoginRequest):
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
            login_time=datetime.datetime.now(timezone.utc)
        )
        session.add(log)
        # Generate access token, etc.
        access_token = secrets.token_urlsafe(64)
        now = datetime.datetime.now(timezone.utc)
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

@router.post('/logout', summary="Logout")
def user_logout(current_user: Employee = Depends(get_current_user)):
    session: Session = SessionLocal()
    try:
        employee = current_user
        if not employee:
            raise HTTPException(status_code=404, detail="User not found")
        login_log = session.query(LoginLog).filter(
            LoginLog.user_id == employee.id,
            LoginLog.logout_time == None
        ).order_by(LoginLog.login_time.desc()).first()
        if login_log:
            setattr(login_log, 'logout_time', datetime.datetime.now(timezone.utc))
            session.commit()
            return {"message": "Logout successful"}
        else:
            raise HTTPException(status_code=400, detail="No active login session found")
    finally:
        session.close()

@router.post('/admin/change-password/{employee_id}', summary="Admin change user password")
def admin_change_user_password(employee_id: int, new_password: str = Body(...), current_user: Employee = Depends(admin_auth)):
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