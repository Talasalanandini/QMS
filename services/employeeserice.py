import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr
from db.database import SessionLocal
from models import Employee
from sqlalchemy.exc import IntegrityError
from passlib.hash import bcrypt
from models import Department, Role
import datetime

# Load SMTP credentials from environment variables
SMTP_SERVER = (os.getenv('SMTP_SERVER') or '').strip()
SMTP_PORT = int((os.getenv('SMTP_PORT', '587') or '587').strip())
SMTP_USER = (os.getenv('SMTP_USER') or '').strip()
SMTP_PASSWORD = (os.getenv('SMTP_PASSWORD') or '').strip().replace(' ', '')
SMTP_FROM_NAME = (os.getenv('SMTP_FROM_NAME', 'QMS') or 'QMS').strip()
SMTP_USE_SSL = (os.getenv('SMTP_USE_SSL', '0') or '0').strip() in ['1', 'true', 'True']

# Utility to generate a random password
def generate_password(length=10):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

# Utility to send email via SMTP
def send_email(to_email: str, subject: str, body: str) -> None:
    """Send an email over SMTP using TLS (587) or SSL (465).

    Requires env vars: SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD.
    For Gmail, use an App Password (2FA) and smtp.gmail.com:587.
    """
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        raise RuntimeError("SMTP configuration missing (SMTP_SERVER/PORT/USER/PASSWORD)")

    from_email = str(SMTP_USER)
    from_header = formataddr((SMTP_FROM_NAME, from_email))

    msg = MIMEText(body, _subtype='plain', _charset='utf-8')
    msg['Subject'] = str(subject)
    msg['From'] = from_header
    msg['To'] = str(to_email)

    try:
        if SMTP_USE_SSL or int(SMTP_PORT) == 465:
            with smtplib.SMTP_SSL(str(SMTP_SERVER), int(SMTP_PORT)) as server:
                server.login(str(SMTP_USER), str(SMTP_PASSWORD))
                server.sendmail(from_email, [str(to_email)], msg.as_string())
        else:
            with smtplib.SMTP(str(SMTP_SERVER), int(SMTP_PORT)) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(str(SMTP_USER), str(SMTP_PASSWORD))
                server.sendmail(from_email, [str(to_email)], msg.as_string())
    except smtplib.SMTPAuthenticationError as e:
        raise RuntimeError("SMTP authentication failed. Check SMTP_USER/SMTP_PASSWORD (use an app password if using Gmail).") from e
    except smtplib.SMTPException as e:
        raise RuntimeError(f"SMTP error: {str(e)}") from e

def create_employee(employee_data):
    session = SessionLocal()
    try:
        # Generate and hash password
        password = generate_password()
        hashed_password = bcrypt.hash(password)
        employee_data['password'] = hashed_password
        employee = Employee(**employee_data)
        session.add(employee)
        session.commit()
        session.refresh(employee)
        # Send email with credentials
        email_body = (
            f"Welcome to QMS!\n\n"
            f"Login Email: {employee.email}\n"
            f"Temporary Password: {password}\n\n"
            f"Please sign in and change your password."
        )
        send_email(employee.email, "Your QMS Login Credentials", email_body)
        # Return employee and password for API response
        department_name = None
        role_name = None
        if employee.department_id:
            department = session.query(Department).filter(Department.id == employee.department_id).first()
            if department:
                department_name = department.name
        if employee.role_id:
            role = session.query(Role).filter(Role.id == employee.role_id).first()
            if role:
                role_name = role.name
        return {
            "id": employee.id,
            "full_name": employee.full_name,
            "email": employee.email,
            "phone": employee.phone,
            "department": department_name,
            "role": role_name,
            "password": password
        }, password
    except IntegrityError:
        session.rollback()
        raise ValueError('Employee with this email already exists')
    finally:
        session.close()

def delete_employee(employee_id: int):
    """Soft delete an employee by setting deleted_at timestamp"""
    session = SessionLocal()
    try:
        # Check if employee exists
        employee = session.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise ValueError("Employee not found")
        
        # Check if employee is already deleted
        if employee.deleted_at:
            raise ValueError("Employee is already deleted")
        
        # Soft delete by setting deleted_at timestamp
        employee.deleted_at = datetime.datetime.utcnow()
        session.commit()
        
        return {
            "success": True,
            "message": f"Employee '{employee.full_name}' has been deleted successfully",
            "employee_id": employee.id,
            "deleted_at": employee.deleted_at.isoformat()
        }
        
    except Exception as e:
        session.rollback()
        raise ValueError(f"Failed to delete employee: {str(e)}")
    finally:
        session.close()

def restore_employee(employee_id: int):
    """Restore a soft-deleted employee by clearing the deleted_at timestamp"""
    session = SessionLocal()
    try:
        # Check if employee exists (including deleted ones)
        employee = session.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise ValueError("Employee not found")
        
        # Check if employee is already active
        if not employee.deleted_at:
            raise ValueError("Employee is already active")
        
        # Restore by clearing deleted_at timestamp
        employee.deleted_at = None
        session.commit()
        
        return {
            "success": True,
            "message": f"Employee '{employee.full_name}' has been restored successfully",
            "employee_id": employee.id,
            "restored_at": datetime.datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        session.rollback()
        raise ValueError(f"Failed to restore employee: {str(e)}")
    finally:
        session.close()
