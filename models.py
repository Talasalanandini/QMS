from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SqlEnum
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from enum import Enum
from pydantic import BaseModel, EmailStr
import datetime

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
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class Department(Base):
    __tablename__ = 'departments'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    employees = relationship("Employee", back_populates="department_obj")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

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
    avatar_url = Column(String, nullable=True)
    signature = Column(String, nullable=True)
    status = Column(String, nullable=True, default='active')
    must_reset_password = Column(Integer, default=1)  # 1 = must reset, 0 = not required
    department_obj = relationship("Department", back_populates="employees")
    role_obj = relationship("Role", back_populates="employees")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class Token(Base):
    __tablename__ = 'tokens'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(String, nullable=False)
    created_at = Column(String, nullable=False)
    revoked = Column(Integer, default=0)  # 0 = not revoked, 1 = revoked
    created_at_ts = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

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

class LoginLog(Base):
    __tablename__ = 'login_logs'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    login_time = Column(DateTime, default=datetime.datetime.utcnow)
    logout_time = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)

class AuditTypeEnum(str, Enum):
    internal = "Internal"
    external = "External"
    compliance = "Compliance"
    regulatory = "Regulatory"
    financial = "Financial"

class Audit(Base):
    __tablename__ = 'audits'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    type = Column(SqlEnum(AuditTypeEnum), nullable=False)
    status = Column(String, nullable=False, default='Scheduled')
    scheduled_date = Column(DateTime, nullable=True)
    lead_auditor_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    scope = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    deleted_at = Column(DateTime, nullable=True)
    creator = relationship("Employee", foreign_keys=[created_by])
    lead_auditor = relationship("Employee", foreign_keys=[lead_auditor_id])

class Feedback(Base):
    __tablename__ = 'feedbacks'
    id = Column(Integer, primary_key=True, index=True)
    audit_id = Column(Integer, ForeignKey('audits.id'), nullable=False)
    auditor_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    feedback = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    audit = relationship("Audit")
    auditor = relationship("Employee")
