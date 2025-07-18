from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum
from pydantic import BaseModel, EmailStr

Base = declarative_base()

class RoleEnum(str, Enum):
    admin = "Admin"
    auditor = "Auditor"
    employee = "Employee"
    approver = "Approver"
    reviewer = "Reviewer"
    qa = "Qa"

class DepartmentEnum(str, Enum):
    production = "Production"
    manufacturing = "Manufacturing"
    human_resources = "Human Resources"
    maintenance = "Maintenance"
    quality_assurance = "Quality Assurance"
    research_development = "Research & Development"
    regulatory_affairs = "Regulatory Affairs"
    engineering = "Engineering"
    finance = "Finance"
    information_technology = "Information Technology"

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    employees = relationship("Employee", back_populates="role_obj")

class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    employees = relationship("Employee", back_populates="department_obj")

class EmployeeBase(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    department: DepartmentEnum
    role: RoleEnum

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    phone = Column(String, nullable=True)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=False)
    password = Column(String, nullable=False)
    department_obj = relationship("Department", back_populates="employees")
    role_obj = relationship("Role", back_populates="employees")

class Token(Base):
    __tablename__ = 'tokens'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    revoked = Column(Integer, default=0)  # 0 = not revoked, 1 = revoked

class LoginResponse(BaseModel):
    message: str
    access_token: str
    expires_at: str

class EmployeeListItem(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    department: str

    class Config:
        orm_mode = True
