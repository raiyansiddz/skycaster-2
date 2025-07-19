"""fix_enum_casing_to_lowercase

Revision ID: 34b68ed65ece
Revises: 9ec8250584c4
Create Date: 2025-07-19 20:51:05.223475

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '34b68ed65ece'
down_revision: Union[str, Sequence[str], None] = '9ec8250584c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix enum casing from uppercase to lowercase to match SQLAlchemy models."""
    
    # Fix subscription_plan enum (FREE -> free, etc.)
    op.execute("ALTER TYPE subscription_plan RENAME TO subscription_plan_old")
    op.execute("CREATE TYPE subscription_plan AS ENUM ('free', 'developer', 'business', 'enterprise')")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN plan TYPE subscription_plan 
        USING CASE 
            WHEN plan::text = 'FREE' THEN 'free'::subscription_plan
            WHEN plan::text = 'DEVELOPER' THEN 'developer'::subscription_plan  
            WHEN plan::text = 'BUSINESS' THEN 'business'::subscription_plan
            WHEN plan::text = 'ENTERPRISE' THEN 'enterprise'::subscription_plan
            ELSE plan::text::subscription_plan
        END
    """)
    op.execute("DROP TYPE subscription_plan_old")
    
    # Fix subscription_status enum (ACTIVE -> active, etc.)
    op.execute("ALTER TYPE subscription_status RENAME TO subscription_status_old")
    op.execute("CREATE TYPE subscription_status AS ENUM ('active', 'cancelled', 'past_due', 'incomplete', 'trialing')")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN status TYPE subscription_status 
        USING CASE 
            WHEN status::text = 'ACTIVE' THEN 'active'::subscription_status
            WHEN status::text = 'CANCELLED' THEN 'cancelled'::subscription_status
            WHEN status::text = 'PAST_DUE' THEN 'past_due'::subscription_status
            WHEN status::text = 'INCOMPLETE' THEN 'incomplete'::subscription_status
            WHEN status::text = 'TRIALING' THEN 'trialing'::subscription_status
            ELSE status::text::subscription_status
        END
    """)
    op.execute("DROP TYPE subscription_status_old")
    
    # Fix other enum types for consistency
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('user', 'admin')")
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE user_role 
        USING CASE 
            WHEN role::text = 'USER' THEN 'user'::user_role
            WHEN role::text = 'ADMIN' THEN 'admin'::user_role
            ELSE role::text::user_role
        END
    """)
    op.execute("DROP TYPE user_role_old")
    
    # Fix ticket_status enum
    op.execute("ALTER TYPE ticket_status RENAME TO ticket_status_old")
    op.execute("CREATE TYPE ticket_status AS ENUM ('open', 'in_progress', 'resolved', 'closed')")
    op.execute("""
        ALTER TABLE support_tickets 
        ALTER COLUMN status TYPE ticket_status 
        USING CASE 
            WHEN status::text = 'OPEN' THEN 'open'::ticket_status
            WHEN status::text = 'IN_PROGRESS' THEN 'in_progress'::ticket_status
            WHEN status::text = 'RESOLVED' THEN 'resolved'::ticket_status
            WHEN status::text = 'CLOSED' THEN 'closed'::ticket_status
            ELSE status::text::ticket_status
        END
    """)
    op.execute("DROP TYPE ticket_status_old")
    
    # Fix ticket_priority enum
    op.execute("ALTER TYPE ticket_priority RENAME TO ticket_priority_old")
    op.execute("CREATE TYPE ticket_priority AS ENUM ('low', 'medium', 'high', 'urgent')")
    op.execute("""
        ALTER TABLE support_tickets 
        ALTER COLUMN priority TYPE ticket_priority 
        USING CASE 
            WHEN priority::text = 'LOW' THEN 'low'::ticket_priority
            WHEN priority::text = 'MEDIUM' THEN 'medium'::ticket_priority
            WHEN priority::text = 'HIGH' THEN 'high'::ticket_priority
            WHEN priority::text = 'URGENT' THEN 'urgent'::ticket_priority
            ELSE priority::text::ticket_priority
        END
    """)
    op.execute("DROP TYPE ticket_priority_old")
    
    # Fix invoice_status enum
    op.execute("ALTER TYPE invoice_status RENAME TO invoice_status_old")
    op.execute("CREATE TYPE invoice_status AS ENUM ('draft', 'open', 'paid', 'void', 'uncollectible')")
    op.execute("""
        ALTER TABLE invoices 
        ALTER COLUMN status TYPE invoice_status 
        USING CASE 
            WHEN status::text = 'DRAFT' THEN 'draft'::invoice_status
            WHEN status::text = 'OPEN' THEN 'open'::invoice_status
            WHEN status::text = 'PAID' THEN 'paid'::invoice_status
            WHEN status::text = 'VOID' THEN 'void'::invoice_status
            WHEN status::text = 'UNCOLLECTIBLE' THEN 'uncollectible'::invoice_status
            ELSE status::text::invoice_status
        END
    """)
    op.execute("DROP TYPE invoice_status_old")


def downgrade() -> None:
    """Revert enum casing from lowercase back to uppercase."""
    
    # Revert subscription_plan enum (free -> FREE, etc.)
    op.execute("ALTER TYPE subscription_plan RENAME TO subscription_plan_old")
    op.execute("CREATE TYPE subscription_plan AS ENUM ('FREE', 'DEVELOPER', 'BUSINESS', 'ENTERPRISE')")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN plan TYPE subscription_plan 
        USING CASE 
            WHEN plan::text = 'free' THEN 'FREE'::subscription_plan
            WHEN plan::text = 'developer' THEN 'DEVELOPER'::subscription_plan
            WHEN plan::text = 'business' THEN 'BUSINESS'::subscription_plan
            WHEN plan::text = 'enterprise' THEN 'ENTERPRISE'::subscription_plan
            ELSE plan::text::subscription_plan
        END
    """)
    op.execute("DROP TYPE subscription_plan_old")
    
    # Revert subscription_status enum
    op.execute("ALTER TYPE subscription_status RENAME TO subscription_status_old")
    op.execute("CREATE TYPE subscription_status AS ENUM ('ACTIVE', 'CANCELLED', 'PAST_DUE', 'INCOMPLETE', 'TRIALING')")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN status TYPE subscription_status 
        USING CASE 
            WHEN status::text = 'active' THEN 'ACTIVE'::subscription_status
            WHEN status::text = 'cancelled' THEN 'CANCELLED'::subscription_status
            WHEN status::text = 'past_due' THEN 'PAST_DUE'::subscription_status
            WHEN status::text = 'incomplete' THEN 'INCOMPLETE'::subscription_status
            WHEN status::text = 'trialing' THEN 'TRIALING'::subscription_status
            ELSE status::text::subscription_status
        END
    """)
    op.execute("DROP TYPE subscription_status_old")
    
    # Revert other enums...
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('USER', 'ADMIN')")
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE user_role 
        USING CASE 
            WHEN role::text = 'user' THEN 'USER'::user_role
            WHEN role::text = 'admin' THEN 'ADMIN'::user_role
            ELSE role::text::user_role
        END
    """)
    op.execute("DROP TYPE user_role_old")
