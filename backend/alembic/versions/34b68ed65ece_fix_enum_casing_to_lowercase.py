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
    
    # Fix subscriptionplan enum (FREE -> free, etc.)
    op.execute("ALTER TYPE subscriptionplan RENAME TO subscriptionplan_old")
    op.execute("CREATE TYPE subscriptionplan AS ENUM ('free', 'developer', 'business', 'enterprise')")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN plan TYPE subscriptionplan 
        USING CASE 
            WHEN plan::text = 'FREE' THEN 'free'::subscriptionplan
            WHEN plan::text = 'DEVELOPER' THEN 'developer'::subscriptionplan  
            WHEN plan::text = 'BUSINESS' THEN 'business'::subscriptionplan
            WHEN plan::text = 'ENTERPRISE' THEN 'enterprise'::subscriptionplan
            ELSE plan::text::subscriptionplan
        END
    """)
    op.execute("DROP TYPE subscriptionplan_old")
    
    # Fix subscriptionstatus enum (ACTIVE -> active, etc.)
    op.execute("ALTER TYPE subscriptionstatus RENAME TO subscriptionstatus_old")
    op.execute("CREATE TYPE subscriptionstatus AS ENUM ('active', 'cancelled', 'past_due', 'incomplete', 'trialing')")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN status TYPE subscriptionstatus 
        USING CASE 
            WHEN status::text = 'ACTIVE' THEN 'active'::subscriptionstatus
            WHEN status::text = 'CANCELLED' THEN 'cancelled'::subscriptionstatus
            WHEN status::text = 'PAST_DUE' THEN 'past_due'::subscriptionstatus
            WHEN status::text = 'INCOMPLETE' THEN 'incomplete'::subscriptionstatus
            WHEN status::text = 'TRIALING' THEN 'trialing'::subscriptionstatus
            ELSE status::text::subscriptionstatus
        END
    """)
    op.execute("DROP TYPE subscriptionstatus_old")
    
    # Fix userrole enum
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM ('user', 'admin')")
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole 
        USING CASE 
            WHEN role::text = 'USER' THEN 'user'::userrole
            WHEN role::text = 'ADMIN' THEN 'admin'::userrole
            ELSE role::text::userrole
        END
    """)
    op.execute("DROP TYPE userrole_old")
    
    # Fix ticketstatus enum
    op.execute("ALTER TYPE ticketstatus RENAME TO ticketstatus_old")
    op.execute("CREATE TYPE ticketstatus AS ENUM ('open', 'in_progress', 'resolved', 'closed')")
    op.execute("""
        ALTER TABLE support_tickets 
        ALTER COLUMN status TYPE ticketstatus 
        USING CASE 
            WHEN status::text = 'OPEN' THEN 'open'::ticketstatus
            WHEN status::text = 'IN_PROGRESS' THEN 'in_progress'::ticketstatus
            WHEN status::text = 'RESOLVED' THEN 'resolved'::ticketstatus
            WHEN status::text = 'CLOSED' THEN 'closed'::ticketstatus
            ELSE status::text::ticketstatus
        END
    """)
    op.execute("DROP TYPE ticketstatus_old")
    
    # Fix ticketpriority enum
    op.execute("ALTER TYPE ticketpriority RENAME TO ticketpriority_old")
    op.execute("CREATE TYPE ticketpriority AS ENUM ('low', 'medium', 'high', 'urgent')")
    op.execute("""
        ALTER TABLE support_tickets 
        ALTER COLUMN priority TYPE ticketpriority 
        USING CASE 
            WHEN priority::text = 'LOW' THEN 'low'::ticketpriority
            WHEN priority::text = 'MEDIUM' THEN 'medium'::ticketpriority
            WHEN priority::text = 'HIGH' THEN 'high'::ticketpriority
            WHEN priority::text = 'URGENT' THEN 'urgent'::ticketpriority
            ELSE priority::text::ticketpriority
        END
    """)
    op.execute("DROP TYPE ticketpriority_old")
    
    # Fix invoicestatus enum
    op.execute("ALTER TYPE invoicestatus RENAME TO invoicestatus_old")
    op.execute("CREATE TYPE invoicestatus AS ENUM ('draft', 'open', 'paid', 'void', 'uncollectible')")
    op.execute("""
        ALTER TABLE invoices 
        ALTER COLUMN status TYPE invoicestatus 
        USING CASE 
            WHEN status::text = 'DRAFT' THEN 'draft'::invoicestatus
            WHEN status::text = 'OPEN' THEN 'open'::invoicestatus
            WHEN status::text = 'PAID' THEN 'paid'::invoicestatus
            WHEN status::text = 'VOID' THEN 'void'::invoicestatus
            WHEN status::text = 'UNCOLLECTIBLE' THEN 'uncollectible'::invoicestatus
            ELSE status::text::invoicestatus
        END
    """)
    op.execute("DROP TYPE invoicestatus_old")


def downgrade() -> None:
    """Revert enum casing from lowercase back to uppercase."""
    
    # Revert subscriptionplan enum (free -> FREE, etc.)
    op.execute("ALTER TYPE subscriptionplan RENAME TO subscriptionplan_old")
    op.execute("CREATE TYPE subscriptionplan AS ENUM ('FREE', 'DEVELOPER', 'BUSINESS', 'ENTERPRISE')")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN plan TYPE subscriptionplan 
        USING CASE 
            WHEN plan::text = 'free' THEN 'FREE'::subscriptionplan
            WHEN plan::text = 'developer' THEN 'DEVELOPER'::subscriptionplan
            WHEN plan::text = 'business' THEN 'BUSINESS'::subscriptionplan
            WHEN plan::text = 'enterprise' THEN 'ENTERPRISE'::subscriptionplan
            ELSE plan::text::subscriptionplan
        END
    """)
    op.execute("DROP TYPE subscriptionplan_old")
    
    # Revert subscriptionstatus enum
    op.execute("ALTER TYPE subscriptionstatus RENAME TO subscriptionstatus_old")
    op.execute("CREATE TYPE subscriptionstatus AS ENUM ('ACTIVE', 'CANCELLED', 'PAST_DUE', 'INCOMPLETE', 'TRIALING')")
    op.execute("""
        ALTER TABLE subscriptions 
        ALTER COLUMN status TYPE subscriptionstatus 
        USING CASE 
            WHEN status::text = 'active' THEN 'ACTIVE'::subscriptionstatus
            WHEN status::text = 'cancelled' THEN 'CANCELLED'::subscriptionstatus
            WHEN status::text = 'past_due' THEN 'PAST_DUE'::subscriptionstatus
            WHEN status::text = 'incomplete' THEN 'INCOMPLETE'::subscriptionstatus
            WHEN status::text = 'trialing' THEN 'TRIALING'::subscriptionstatus
            ELSE status::text::subscriptionstatus
        END
    """)
    op.execute("DROP TYPE subscriptionstatus_old")
    
    # Revert userrole enum
    op.execute("ALTER TYPE userrole RENAME TO userrole_old")
    op.execute("CREATE TYPE userrole AS ENUM ('USER', 'ADMIN')")
    op.execute("""
        ALTER TABLE users 
        ALTER COLUMN role TYPE userrole 
        USING CASE 
            WHEN role::text = 'user' THEN 'USER'::userrole
            WHEN role::text = 'admin' THEN 'ADMIN'::userrole
            ELSE role::text::userrole
        END
    """)
    op.execute("DROP TYPE userrole_old")
