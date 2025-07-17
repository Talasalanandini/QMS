from db.database import SessionLocal
from models import Employee, Role, Department
from passlib.hash import bcrypt

def ensure_admin_user():
    session = SessionLocal()
    try:
        # Ensure Admin role exists
        admin_role = session.query(Role).filter(Role.name == "Admin").first()
        if not admin_role:
            admin_role = Role(name="Admin")
            session.add(admin_role)
            session.commit()
            session.refresh(admin_role)

        # Ensure at least one department exists
        department = session.query(Department).first()
        if not department:
            department = Department(name="General")
            session.add(department)
            session.commit()
            session.refresh(department)

        # Ensure admin user exists
        admin_email = "admin@gmail.com"
        admin_user = session.query(Employee).filter(Employee.email == admin_email).first()
        if not admin_user:
            hashed_password = bcrypt.hash("admin@123")
            admin_user = Employee(
                full_name="Admin",
                email=admin_email,
                phone="1234567890",
                department_id=department.id,
                role_id=admin_role.id,
                password=hashed_password
            )
            session.add(admin_user)
            session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")
    finally:
        session.close() 