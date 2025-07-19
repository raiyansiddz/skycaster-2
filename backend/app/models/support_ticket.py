from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base

class TicketStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"

class TicketPriority(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Ticket details
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(TicketStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TicketStatus.OPEN)
    priority = Column(Enum(TicketPriority, values_callable=lambda x: [e.value for e in x]), nullable=False, default=TicketPriority.MEDIUM)
    
    # Assignment
    assigned_to = Column(String)  # Admin user ID
    
    # Resolution
    resolution = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="support_tickets")
    
    def __repr__(self):
        return f"<SupportTicket(id={self.id}, title={self.title}, user_id={self.user_id})>"