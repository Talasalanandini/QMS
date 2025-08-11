"""create workflow tables

Revision ID: workflow_001
Revises: f62b1e6eb486
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'workflow_001'
down_revision = 'f62b1e6eb486'
branch_labels = None
depends_on = None

def upgrade():
    # Create workflow_types enum
    op.execute("CREATE TYPE workflowtypeenum AS ENUM ('Document Approval', 'Training', 'Audit', 'Quality Check', 'Compliance', 'Incident')")
    
    # Create workflow_status_enum
    op.execute("CREATE TYPE workflowstatusenum AS ENUM ('active', 'inactive', 'draft', 'archived')")
    
    # Create block_type_enum
    op.execute("CREATE TYPE blocktypeenum AS ENUM ('Start', 'End', 'Internal Actor', 'External Actor', 'Condition', 'Rules')")
    
    # Create workflows table
    op.create_table('workflows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('workflow_type', sa.Enum('Document Approval', 'Training', 'Audit', 'Quality Check', 'Compliance', 'Incident', name='workflowtypeenum'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', 'draft', 'archived', name='workflowstatusenum'), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['employees.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflows_id'), 'workflows', ['id'], unique=False)
    
    # Create workflow_blocks table
    op.create_table('workflow_blocks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('block_type', sa.Enum('Start', 'End', 'Internal Actor', 'External Actor', 'Condition', 'Rules', name='blocktypeenum'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('configuration', sa.JSON(), nullable=True),
        sa.Column('position_x', sa.Integer(), nullable=False),
        sa.Column('position_y', sa.Integer(), nullable=False),
        sa.Column('lane_v', sa.Integer(), nullable=True),
        sa.Column('lane_h', sa.Integer(), nullable=True),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_blocks_id'), 'workflow_blocks', ['id'], unique=False)
    
    # Create workflow_connections table
    op.create_table('workflow_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('from_block_id', sa.Integer(), nullable=False),
        sa.Column('to_block_id', sa.Integer(), nullable=False),
        sa.Column('condition', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['from_block_id'], ['workflow_blocks.id'], ),
        sa.ForeignKeyConstraint(['to_block_id'], ['workflow_blocks.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_connections_id'), 'workflow_connections', ['id'], unique=False)
    
    # Create workflow_instances table
    op.create_table('workflow_instances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workflow_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('current_block_id', sa.Integer(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('started_by', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['current_block_id'], ['workflow_blocks.id'], ),
        sa.ForeignKeyConstraint(['started_by'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['workflow_id'], ['workflows.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_instances_id'), 'workflow_instances', ['id'], unique=False)
    
    # Create workflow_activities table
    op.create_table('workflow_activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instance_id', sa.Integer(), nullable=False),
        sa.Column('block_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['actor_id'], ['employees.id'], ),
        sa.ForeignKeyConstraint(['block_id'], ['workflow_blocks.id'], ),
        sa.ForeignKeyConstraint(['instance_id'], ['workflow_instances.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workflow_activities_id'), 'workflow_activities', ['id'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_workflow_activities_id'), table_name='workflow_activities')
    op.drop_table('workflow_activities')
    op.drop_index(op.f('ix_workflow_instances_id'), table_name='workflow_instances')
    op.drop_table('workflow_instances')
    op.drop_index(op.f('ix_workflow_connections_id'), table_name='workflow_connections')
    op.drop_table('workflow_connections')
    op.drop_index(op.f('ix_workflow_blocks_id'), table_name='workflow_blocks')
    op.drop_table('workflow_blocks')
    op.drop_index(op.f('ix_workflows_id'), table_name='workflows')
    op.drop_table('workflows')
    
    # Drop enums
    op.execute("DROP TYPE blocktypeenum")
    op.execute("DROP TYPE workflowstatusenum")
    op.execute("DROP TYPE workflowtypeenum") 