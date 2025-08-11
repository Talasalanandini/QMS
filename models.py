from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum as SqlEnum, Text, Boolean, JSON, Float
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
        from_attributes = True

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
    end_date = Column(DateTime, nullable=True)
    lead_auditor_id = Column(Integer, ForeignKey('employees.id'), nullable=True)
    scope = Column(String, nullable=True)
    target_department = Column(String, nullable=True)
    observations = Column(Text, nullable=True)
    findings = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    signature = Column(String, nullable=True)
    signed_date = Column(DateTime, nullable=True)
    auditor_name = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
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

class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False)
    timezone = Column(String, nullable=True, default='UTC')
    logo_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class DocumentTypeEnum(str, Enum):
    standard_operating_procedure = "Standard Operating Procedure"
    policy = "Policy"
    manual = "Manual"
    specification = "Specification"
    report = "Report"
    form = "Form"
    protocol = "Protocol"
    certificate = "Certificate"

class DocumentStatusEnum(str, Enum):
    draft = "draft"
    under_review = "under_review"
    under_approval = "under_approval"
    approved = "approved"
    rejected = "rejected"
    archived = "archived"

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    document_type = Column(SqlEnum(DocumentTypeEnum), nullable=False)
    file_path = Column(String, nullable=True)  # Path to stored PDF file (optional when using base64)
    file_name = Column(String, nullable=False)  # Original filename
    file_size = Column(Integer, nullable=True)  # File size in bytes
    file_base64 = Column(Text, nullable=True)  # Base64 encoded file content
    version = Column(String, nullable=False, default='1.0')
    status = Column(SqlEnum(DocumentStatusEnum), nullable=False, default=DocumentStatusEnum.draft)
    content = Column(String, nullable=True)  # Optional content/description
    uploaded_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    assigned_approver_id = Column(Integer, ForeignKey('employees.id'), nullable=True)  # Assigned approver
    approved_by = Column(Integer, ForeignKey('employees.id'), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    uploader = relationship("Employee", foreign_keys=[uploaded_by])
    assigned_approver = relationship("Employee", foreign_keys=[assigned_approver_id])
    approver = relationship("Employee", foreign_keys=[approved_by])

class DocumentReview(Base):
    __tablename__ = 'document_reviews'
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    reviewer_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    action = Column(String, nullable=False)  # "review", "reject", "approve"
    signature = Column(String, nullable=True)  # Base64 encoded signature
    comments = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    document = relationship("Document")
    reviewer = relationship("Employee", foreign_keys=[reviewer_id])

class DocumentView(Base):
    __tablename__ = 'document_views'
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    viewer_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    viewer_name = Column(String, nullable=False)  # Store name at time of viewing
    viewer_role = Column(String, nullable=False)  # Store role at time of viewing
    viewed_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    document = relationship("Document")
    viewer = relationship("Employee", foreign_keys=[viewer_id])

# Training Management Models
class TrainingTypeEnum(str, Enum):
    compliance = "Compliance"
    leadership = "Leadership"
    onboarding = "Onboarding"
    process = "Process"
    quality = "Quality"
    refresher = "Refresher"
    safety = "Safety"
    technical = "Technical"

class TrainingStatusEnum(str, Enum):
    scheduled = "Scheduled"
    in_progress = "In Progress"
    completed = "Completed"
    cancelled = "Cancelled"

class Training(Base):
    __tablename__ = 'trainings'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    # New fields for enhanced training creation
    course_code = Column(String, nullable=True)
    passing_score = Column(Integer, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    mandatory = Column(Boolean, default=False)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    training_type = Column(SqlEnum(TrainingTypeEnum), nullable=False)
    trainer_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    duration_hours = Column(Integer, nullable=True)  # Optional duration in hours
    assigned_date = Column(DateTime, nullable=False)
    description = Column(String, nullable=True)  # Training description/content
    status = Column(SqlEnum(TrainingStatusEnum), nullable=False, default=TrainingStatusEnum.scheduled)
    created_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # File upload fields
    content_type = Column(String, nullable=True)  # "document" or "video"
    file_path = Column(String, nullable=True)  # Path to stored file
    file_name = Column(String, nullable=True)  # Original filename
    file_size = Column(Integer, nullable=True)  # File size in bytes
    file_type = Column(String, nullable=True)  # File extension/mime type
    file_base64 = Column(Text, nullable=True)  # Base64 encoded file content for videos
    
    # Relationships
    department = relationship("Department")
    trainer = relationship("Employee", foreign_keys=[trainer_id])
    creator = relationship("Employee", foreign_keys=[created_by])

# Training Assignment Models
class TrainingAssignmentStatusEnum(str, Enum):
    assigned = "Assigned"
    in_progress = "In Progress"
    completed = "Completed"
    cancelled = "Cancelled"

class TrainingAssignment(Base):
    __tablename__ = 'training_assignments'
    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey('trainings.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    assigned_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    assigned_date = Column(DateTime, default=datetime.datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    status = Column(SqlEnum(TrainingAssignmentStatusEnum), nullable=False, default=TrainingAssignmentStatusEnum.assigned)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    training = relationship("Training")
    employee = relationship("Employee", foreign_keys=[employee_id])
    assigned_by_user = relationship("Employee", foreign_keys=[assigned_by])

# Company Training Assignment Models
class CompanyTrainingAssignment(Base):
    __tablename__ = 'company_training_assignments'
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    training_id = Column(Integer, ForeignKey('trainings.id'), nullable=False)
    assigned_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    assigned_date = Column(DateTime, default=datetime.datetime.utcnow)
    due_date = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    company = relationship("Client")
    training = relationship("Training")
    assigned_by_user = relationship("Employee", foreign_keys=[assigned_by])

class ProjectStatusEnum(str, Enum):
    not_started = "Not Started"
    in_progress = "In Progress"
    on_hold = "On Hold"
    completed = "Completed"
    cancelled = "Cancelled"

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SqlEnum(ProjectStatusEnum), nullable=False, default=ProjectStatusEnum.not_started)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    project_manager_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=False)
    created_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    project_manager = relationship("Employee", foreign_keys=[project_manager_id])
    department = relationship("Department")
    creator = relationship("Employee", foreign_keys=[created_by])
    assigned_employees = relationship("ProjectEmployeeAssignment", back_populates="project")

class ProjectEmployeeAssignment(Base):
    __tablename__ = 'project_employee_assignments'
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    assigned_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    assigned_date = Column(DateTime, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    project = relationship("Project", back_populates="assigned_employees")
    employee = relationship("Employee", foreign_keys=[employee_id])
    assigned_by_user = relationship("Employee", foreign_keys=[assigned_by])

# Work Order Management Models
class WorkOrderPriorityEnum(str, Enum):
    low = "Low"
    medium = "Medium"
    high = "High"
    critical = "Critical"

class WorkOrderStatusEnum(str, Enum):
    draft = "Draft"
    pending = "Pending"
    in_progress = "In Progress"
    on_hold = "On Hold"
    completed = "Completed"
    cancelled = "Cancelled"
    rejected = "Rejected"

class WorkOrderTypeEnum(str, Enum):
    maintenance = "Maintenance"
    repair = "Repair"
    inspection = "Inspection"
    calibration = "Calibration"
    installation = "Installation"
    modification = "Modification"
    emergency = "Emergency"
    preventive = "Preventive"

class TaskStatusEnum(str, Enum):
    pending = "Pending"
    in_progress = "In Progress"
    completed = "Completed"
    failed = "Failed"
    skipped = "Skipped"

class WorkOrder(Base):
    __tablename__ = 'work_orders'
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_number = Column(String, unique=True, nullable=False)  # Auto-generated WO-2024-001
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    work_order_type = Column(SqlEnum(WorkOrderTypeEnum), nullable=False)
    priority = Column(SqlEnum(WorkOrderPriorityEnum), default=WorkOrderPriorityEnum.medium)
    status = Column(SqlEnum(WorkOrderStatusEnum), default=WorkOrderStatusEnum.draft)
    
    # Assignment
    assigned_to = Column(Integer, ForeignKey('employees.id'), nullable=True)
    assigned_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    
    # Dates
    created_date = Column(DateTime, default=datetime.datetime.utcnow)
    scheduled_date = Column(DateTime, nullable=True)
    due_date = Column(DateTime, nullable=True)
    start_date = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    
    # Location and Equipment
    location = Column(String, nullable=True)
    equipment_id = Column(String, nullable=True)
    equipment_name = Column(String, nullable=True)
    
    # Cost and Time Tracking
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)
    
    # Additional Info
    department_id = Column(Integer, ForeignKey('departments.id'), nullable=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=True)
    related_document_id = Column(Integer, ForeignKey('documents.id'), nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    assignee = relationship("Employee", foreign_keys=[assigned_to])
    assigner = relationship("Employee", foreign_keys=[assigned_by])
    department = relationship("Department")
    client = relationship("Client")
    related_document = relationship("Document")
    tasks = relationship("WorkOrderTask", back_populates="work_order")
    activities = relationship("WorkOrderActivity", back_populates="work_order")
    attachments = relationship("WorkOrderAttachment", back_populates="work_order")

class WorkOrderTask(Base):
    __tablename__ = 'work_order_tasks'
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), nullable=False)
    task_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SqlEnum(TaskStatusEnum), default=TaskStatusEnum.pending)
    
    # Assignment
    assigned_to = Column(Integer, ForeignKey('employees.id'), nullable=True)
    
    # Timing
    estimated_hours = Column(Float, nullable=True)
    actual_hours = Column(Float, nullable=True)
    start_time = Column(DateTime, nullable=True)
    completion_time = Column(DateTime, nullable=True)
    
    # Order and Dependencies
    task_order = Column(Integer, nullable=False)
    depends_on_task_id = Column(Integer, ForeignKey('work_order_tasks.id'), nullable=True)
    
    # Additional
    instructions = Column(Text, nullable=True)
    required_tools = Column(String, nullable=True)
    required_materials = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="tasks")
    assignee = relationship("Employee", foreign_keys=[assigned_to])
    depends_on = relationship("WorkOrderTask", remote_side=[id])

class WorkOrderActivity(Base):
    __tablename__ = 'work_order_activities'
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('work_order_tasks.id'), nullable=True)
    
    # Activity Details
    activity_type = Column(String, nullable=False)  # status_change, comment, time_log, etc.
    description = Column(Text, nullable=False)
    performed_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    
    # Data
    data = Column(JSON, nullable=True)  # Additional activity data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="activities")
    task = relationship("WorkOrderTask")
    performer = relationship("Employee", foreign_keys=[performed_by])

class WorkOrderAttachment(Base):
    __tablename__ = 'work_order_attachments'
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), nullable=False)
    
    # File Details
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)
    
    # Metadata
    uploaded_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
    description = Column(Text, nullable=True)
    
    # Relationships
    work_order = relationship("WorkOrder", back_populates="attachments")
    uploader = relationship("Employee", foreign_keys=[uploaded_by])

class WorkOrderTemplate(Base):
    __tablename__ = 'work_order_templates'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    work_order_type = Column(SqlEnum(WorkOrderTypeEnum), nullable=False)
    
    # Template Data
    default_priority = Column(SqlEnum(WorkOrderPriorityEnum), default=WorkOrderPriorityEnum.medium)
    estimated_hours = Column(Float, nullable=True)
    estimated_cost = Column(Float, nullable=True)
    
    # Template Tasks
    tasks_template = Column(JSON, nullable=True)  # Array of task templates
    
    # Metadata
    created_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    creator = relationship("Employee", foreign_keys=[created_by])

class WorkOrderComment(Base):
    __tablename__ = 'work_order_comments'
    
    id = Column(Integer, primary_key=True, index=True)
    work_order_id = Column(Integer, ForeignKey('work_orders.id'), nullable=False)
    task_id = Column(Integer, ForeignKey('work_order_tasks.id'), nullable=True)
    
    # Comment Details
    comment = Column(Text, nullable=False)
    comment_type = Column(String, default='general')  # general, instruction, note, etc.
    
    # Metadata
    created_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    work_order = relationship("WorkOrder")
    task = relationship("WorkOrderTask")
    author = relationship("Employee", foreign_keys=[created_by])

# Assessment Models
class DifficultyLevelEnum(str, Enum):
    easy = "Easy"
    medium = "Medium"
    hard = "Hard"

class AssessmentQuestion(Base):
    __tablename__ = 'assessment_questions'
    
    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey('trainings.id'), nullable=False)
    question_text = Column(Text, nullable=False)
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    correct_option = Column(String, nullable=False)  # "A", "B", "C", or "D"
    difficulty_level = Column(SqlEnum(DifficultyLevelEnum), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    training = relationship("Training")

class AssessmentSubmission(Base):
    __tablename__ = 'assessment_submissions'
    
    id = Column(Integer, primary_key=True, index=True)
    training_id = Column(Integer, ForeignKey('trainings.id'), nullable=False)
    employee_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    score = Column(Integer, nullable=True)  # Percentage score
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    passed = Column(Boolean, nullable=False)  # True if score >= passing_score
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    training = relationship("Training")
    employee = relationship("Employee")

class AssessmentAnswer(Base):
    __tablename__ = 'assessment_answers'
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey('assessment_submissions.id'), nullable=False)
    question_id = Column(Integer, ForeignKey('assessment_questions.id'), nullable=False)
    selected_option = Column(String, nullable=False)  # "A", "B", "C", or "D"
    is_correct = Column(Boolean, nullable=False)
    
    # Relationships
    submission = relationship("AssessmentSubmission")
    question = relationship("AssessmentQuestion")
