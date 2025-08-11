"""create work order tables

Revision ID: workorder_001
Revises: workflow_001
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'workorder_001'
down_revision = 'workflow_001'
branch_labels = None
depends_on = None

def upgrade():
    # Create work order priority enum
    op.execute("CREATE TYPE workorderpriorityenum AS ENUM ('Low', 'Medium', 'High', 'Critical')")
    
    # Create work order status enum
    op.execute("CREATE TYPE workorderstatusenum AS ENUM ('Draft', 'Pending', 'In Progress', 'On Hold', 'Completed', 'Cancelled', 'Rejected')")
    
    # Create work order type enum
    op.execute("CREATE TYPE workordertypeenum AS ENUM ('Maintenance', 'Repair', 'Inspection', 'Calibration', 'Installation', 'Modification', 'Emergency', 'Preventive')")
    
    # Create task status enum
    op.execute("CREATE TYPE taskstatusenum AS ENUM ('Pending', 'In Progress', 'Completed', 'Failed', 'Skipped')")
    
    # Create work_orders table
    op.create_table('work_orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('work_order_number', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('work_order_type', sa.Enum('Maintenance', 'Repair', 'Inspection', 'Calibration', 'Installation', 'Modification', 'Emergency', 'Preventive', name='workordertypeenum'), nullable=False),
        sa.Column('priority', sa.Enum('Low', 'Medium', 'High', 'Critical', name='workorderpriorityenum'), nullable=True),
        sa.Column('status', sa.Enum('Draft', 'Pending', 'In Progress', 'On Hold', 'Completed', 'Cancelled', 'Rejected', name='workorderstatusenum'), nullable=True),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('assigned_by', sa.Integer(), nullable=False),
        sa.Column('created_date', sa.DateTime(), nullable=True),
        sa.Column('scheduled_date', sa.DateTime(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('completion_date', sa.DateTime(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('equipment_id', sa.String(), nullable=True),
        sa.Column('equipment_name', sa.String(), nullable=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('actual_cost', sa.Float(), nullable=True),
        sa.Column('department_id', sa.Integer(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('related_document_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['assigned_by'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['related_document_id'], ['documents.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('work_order_number')
    )
    op.create_index(op.f('ix_work_orders_id'), 'work_orders', ['id'], unique=False)
    
    # Create work_order_tasks table
    op.create_table('work_order_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('work_order_id', sa.Integer(), nullable=False),
        sa.Column('task_name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('Pending', 'In Progress', 'Completed', 'Failed', 'Skipped', name='taskstatusenum'), nullable=True),
        sa.Column('assigned_to', sa.Integer(), nullable=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('actual_hours', sa.Float(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('completion_time', sa.DateTime(), nullable=True),
        sa.Column('task_order', sa.Integer(), nullable=False),
        sa.Column('depends_on_task_id', sa.Integer(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('required_tools', sa.String(), nullable=True),
        sa.Column('required_materials', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['depends_on_task_id'], ['work_order_tasks.id'], ),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_order_tasks_id'), 'work_order_tasks', ['id'], unique=False)
    
    # Create work_order_activities table
    op.create_table('work_order_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('work_order_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('performed_by', sa.Integer(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['performed_by'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['work_order_tasks.id'], ),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_order_activities_id'), 'work_order_activities', ['id'], unique=False)
    
    # Create work_order_attachments table
    op.create_table('work_order_attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('work_order_id', sa.Integer(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('file_type', sa.String(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_order_attachments_id'), 'work_order_attachments', ['id'], unique=False)
    
    # Create work_order_templates table
    op.create_table('work_order_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('work_order_type', sa.Enum('Maintenance', 'Repair', 'Inspection', 'Calibration', 'Installation', 'Modification', 'Emergency', 'Preventive', name='workordertypeenum'), nullable=False),
        sa.Column('default_priority', sa.Enum('Low', 'Medium', 'High', 'Critical', name='workorderpriorityenum'), nullable=True),
        sa.Column('estimated_hours', sa.Float(), nullable=True),
        sa.Column('estimated_cost', sa.Float(), nullable=True),
        sa.Column('tasks_template', sa.JSON(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_order_templates_id'), 'work_order_templates', ['id'], unique=False)
    
    # Create work_order_comments table
    op.create_table('work_order_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('work_order_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('comment_type', sa.String(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['work_order_tasks.id'], ),
        sa.ForeignKeyConstraint(['work_order_id'], ['work_orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_work_order_comments_id'), 'work_order_comments', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_work_order_comments_id'), table_name='work_order_comments')
    op.drop_table('work_order_comments')
    op.drop_index(op.f('ix_work_order_templates_id'), table_name='work_order_templates')
    op.drop_table('work_order_templates')
    op.drop_index(op.f('ix_work_order_attachments_id'), table_name='work_order_attachments')
    op.drop_table('work_order_attachments')
    op.drop_index(op.f('ix_work_order_activities_id'), table_name='work_order_activities')
    op.drop_table('work_order_activities')
    op.drop_index(op.f('ix_work_order_tasks_id'), table_name='work_order_tasks')
    op.drop_table('work_order_tasks')
    op.drop_index(op.f('ix_work_orders_id'), table_name='work_orders')
    op.drop_table('work_orders')
    
    # Drop enums
    op.execute("DROP TYPE taskstatusenum")
    op.execute("DROP TYPE workordertypeenum")
    op.execute("DROP TYPE workorderstatusenum")
    op.execute("DROP TYPE workorderpriorityenum") 