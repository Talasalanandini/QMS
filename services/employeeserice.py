import os
import random
import string
import smtplib
from email.mime.text import MIMEText
from db.database import SessionLocal
from models import Employee
from sqlalchemy.exc import IntegrityError
from passlib.hash import bcrypt
from models import Department, Role

# Load SMTP credentials from environment variables
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# Utility to generate a random password
def generate_password(length=10):
    chars = string.ascii_letters + string.digits + string.punctuation
    return ''.join(random.choice(chars) for _ in range(length))

# Utility to send email via SMTP
def send_email(to_email, subject, body):
    print("SMTP_SERVER:", SMTP_SERVER)
    print("SMTP_PORT:", SMTP_PORT)
    print("SMTP_USER:", SMTP_USER)
    print("SMTP_PASSWORD:", SMTP_PASSWORD)
    if not all([SMTP_SERVER, SMTP_PORT, SMTP_USER, SMTP_PASSWORD]):
        raise RuntimeError("SMTP configuration is missing in environment variables.")
    from_email = str(SMTP_USER) if SMTP_USER else ''
    msg = MIMEText(body)
    msg['Subject'] = str(subject)
    msg['From'] = from_email
    msg['To'] = str(to_email)
    with smtplib.SMTP(str(SMTP_SERVER), int(SMTP_PORT)) as server:
        server.starttls()
        server.login(str(SMTP_USER), str(SMTP_PASSWORD))
        server.sendmail(from_email, [str(to_email)], msg.as_string())

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
        email_body = f"Welcome! Your login email: {employee.email}\nPassword: {password}"
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
